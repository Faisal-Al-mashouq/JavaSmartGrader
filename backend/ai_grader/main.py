from __future__ import annotations

import argparse
import asyncio
import logging

from .adapters import (
    PlaceholderDatabaseAdapter,
    RedisQueueAdapter,
    create_database_adapter,
)
from .config import Settings, load_settings
from .llm_client import LLMAPIError, LLMClient
from .parser_validator import (
    JSONValidationError,
    grading_schema,
    parse_and_validate_json,
    validate_submission_id,
)
from .prompt_builder import construct_prompt, construct_repair_prompt

"""
The orchestration layer
Contain:
    the worker loop
    the per-job processing logic
    the repair attempt flow 
    the CLI entry point
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def _parse_with_single_repair(
    *,
    submission_id: int,
    first_response_text: str,
    llm_client: LLMClient,
) -> tuple[dict, str]:
    """
    attempts to parse and validate the first LLM response
    if validation fails (JSONValidationError)
    it constructs a repair prompt and makes exactly one additional LLM call
    if the repair response also fails validation, JSONValidationError is re-raised
    This is the only place where repair logic lives, keeping main process_submission clean
    returns: (parsed_dict, raw_json_string_that_was_used)
    notes: maximum two LLM calls per job: one main + one repair
    """

    schema = grading_schema()
    try:
        parsed = parse_and_validate_json(first_response_text)
        validate_submission_id(parsed, submission_id)
        return parsed, first_response_text
    except JSONValidationError as first_error:
        logger.warning(
            "Invalid JSON for submission_id=%s. Triggering one repair attempt: %s",
            submission_id,
            first_error,
        )

    repair_prompt = construct_repair_prompt(
        submission_id=submission_id,
        previous_output=first_response_text,
        schema=schema,
    )
    repair_response = await llm_client.call(repair_prompt, submission_id=submission_id)

    parsed = parse_and_validate_json(repair_response.text)
    validate_submission_id(parsed, submission_id)
    return parsed, repair_response.text


async def process_submission(
    *,
    submission_id: int,
    db_adapter,
    llm_client: LLMClient,
    settings: Settings,
) -> None:
    """
    core per-job handler
    fetches code, logs, and rubric from DB
    builds and sends the prompt
    calls _parse_with_single_repair, On success:
        saves feedback and updates status
    On LLM failure:
        logs and returns without saving.
    On parse failure:
        persists a failure record and attempts a failure status update
    """
    logger.info("Processing AI grading for submission_id=%s", submission_id)

    code = await db_adapter.get_transcription(submission_id)
    logs = await db_adapter.get_sandbox_results(submission_id)
    rubric = await db_adapter.get_rubric(submission_id)

    schema = grading_schema()
    prompt = construct_prompt(
        submission_id=submission_id,
        code=code,
        logs=logs,
        rubric=rubric,
        schema=schema,
    )

    try:
        response = await llm_client.call(prompt, submission_id=submission_id)
    except LLMAPIError as exc:
        logger.error(
            "LLM call failed for submission_id=%s after retries: %s",
            submission_id,
            exc,
        )
        return

    try:
        parsed, raw_json_used = await _parse_with_single_repair(
            submission_id=submission_id,
            first_response_text=response.text,
            llm_client=llm_client,
        )
    except (JSONValidationError, LLMAPIError) as exc:
        logger.error(
            "Could not produce valid grading JSON for submission_id=%s: %s",
            submission_id,
            exc,
        )
        try:
            await db_adapter.persist_failure_feedback(
                submission_id=submission_id,
                reason=str(exc),
                raw_output=response.text,
            )
            failure_status_set = await db_adapter.mark_failure_status(
                submission_id=submission_id,
                candidates=settings.failure_status_candidates,
            )
            if not failure_status_set:
                logger.warning(
                    "No compatible failure state found for submission_id=%s. "
                    "Status unchanged.",
                    submission_id,
                )
        except Exception as db_exc:
            logger.error(
                "Failed to persist grading failure details for submission_id=%s: %s",
                submission_id,
                db_exc,
            )
        return

    await db_adapter.save_feedback(submission_id=submission_id, parsed_feedback=parsed)

    status_updated = await db_adapter.update_status(
        submission_id=submission_id,
        new_status=settings.pending_review_status,
    )
    if not status_updated:
        logger.warning(
            "Could not set status '%s' for submission_id=%s. "
            "Feedback saved successfully.",
            settings.pending_review_status,
            submission_id,
        )
    else:
        logger.info(
            "AI grading completed for submission_id=%s. Status updated to '%s'.",
            submission_id,
            settings.pending_review_status,
        )

    logger.debug(
        "Final JSON payload for submission_id=%s: %s",
        submission_id,
        raw_json_used,
    )


async def run_worker(*, settings: Settings, once: bool = False) -> None:
    queue_adapter = RedisQueueAdapter(
        redis_url=settings.redis_url,
        poll_timeout_s=settings.queue_poll_timeout_s,
    )

    """
    Initialises the Redis queue adapter, DB adapter, and LLM client
    enters a continuous loop calling queue_adapter.dequeue()
    for each job received, calls process_submission inside a broad try/except so 
    a crash on one job never kills the worker
    if once is passed, exits after the first job (or immediately if no job is available)
    notes: raises RuntimeError at startup if the DB adapter is still a placeholder

    """
    db_adapter = create_database_adapter(settings.backend_path)
    llm_client = LLMClient(settings)

    if isinstance(db_adapter, PlaceholderDatabaseAdapter):
        raise RuntimeError(
            "DB adapter is placeholder; cannot run worker until adapter mapping is configured."
        )

    logger.info(
        "AI Grader worker started. queue=%s redis=%s",
        settings.ready_queue_name,
        settings.redis_url,
    )

    processed_count = 0
    try:
        while True:
            job = await queue_adapter.dequeue(settings.ready_queue_name)
            if job is None:
                if once and processed_count == 0:
                    logger.info(
                        "No job received from queue '%s'.",
                        settings.ready_queue_name,
                    )
                    return
                continue

            processed_count += 1
            try:
                await process_submission(
                    submission_id=job.submission_id,
                    db_adapter=db_adapter,
                    llm_client=llm_client,
                    settings=settings,
                )
            except Exception:
                logger.exception(
                    "Unhandled worker error while processing submission_id=%s",
                    job.submission_id,
                )

            if once:
                logger.info("Processed one job and exiting due to --once.")
                return
    finally:
        await queue_adapter.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI grading worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one job if available, then exit.",
    )
    """
    Parses the once CLI flag using argparse
    returns: argparse.Namespace

    """
    return parser.parse_args()


def main() -> int:
    """
    entry point
    calls load_settings(), then asyncio.run(run_worker(...))
    handles KeyboardInterrupt gracefully
    Returns 0 on normal exit
    returns: int (exit code)
    """
    args = _parse_args()
    settings = load_settings()
    try:
        asyncio.run(run_worker(settings=settings, once=args.once))
        return 0
    except KeyboardInterrupt:
        logger.info("AI Grader worker stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
