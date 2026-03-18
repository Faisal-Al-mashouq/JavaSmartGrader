from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any

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
    This is the only place where repair logic lives, keeping main
    process_submission clean
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
    payload_inputs: dict | None = None,
) -> dict:
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

    if payload_inputs:
        code = payload_inputs.get("code", "")
        logs = payload_inputs.get("logs", "")
        rubric = payload_inputs.get("rubric", {})
    else:
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
        return {"status": "FAILED", "error": str(exc)}

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
        return {
            "status": "FAILED",
            "error": str(exc),
            "raw_output": response.text,
        }

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
    return {
        "status": "COMPLETED",
        "parsed_feedback": parsed,
    }


def _build_completion_payload(
    *,
    job,
    outcome: dict,
) -> dict:
    payload = {
        "job_id": job.job_id,
        "submission_id": job.submission_id,
        "status": outcome.get("status", "FAILED"),
    }

    if payload["status"] == "COMPLETED":
        parsed = outcome.get("parsed_feedback") or {}
        payload["rubric_result_json"] = parsed
        if isinstance(parsed, dict) and "total_score" in parsed:
            try:
                payload["final_grade"] = float(parsed["total_score"])
            except (TypeError, ValueError):
                payload["final_grade"] = None
        summary = (
            parsed.get("feedback", {}).get("summary")
            if isinstance(parsed, dict)
            else None
        )
        if summary:
            payload["student_feedback"] = summary
        return payload

    error = outcome.get("error")
    if error:
        payload["error"] = error
    raw_output = outcome.get("raw_output")
    if raw_output:
        payload["raw_output"] = raw_output
    return payload


def _coerce_lines(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value)


def _format_sandbox_logs(sandbox_result: dict | None) -> str:
    if not sandbox_result or not isinstance(sandbox_result, dict):
        return ""

    result = sandbox_result.get("result")
    if not isinstance(result, dict):
        return ""

    compilation = result.get("compilation_result") or {}
    execution = result.get("execution_result") or {}
    test_cases = result.get("test_cases_results") or {}

    outputs = execution.get("outputs") or []
    output_lines = []
    for index, output in enumerate(outputs, start=1):
        if not isinstance(output, dict):
            continue
        test_case = output.get("test_case") or {}
        output_lines.append(
            "case {idx}: returncode={returncode}\nstdout:\n{stdout}\n"
            "stderr:\n{stderr}\n"
            "input={input}\nexpected={expected}\nactual={actual}".format(
                idx=index,
                returncode=output.get("returncode"),
                stdout=_coerce_lines(output.get("stdout")),
                stderr=_coerce_lines(output.get("stderr")),
                input=test_case.get("input"),
                expected=test_case.get("expected_output"),
                actual=output.get("stdout"),
            )
        )

    test_results = test_cases.get("results") or []
    test_case_lines = []
    for index, case in enumerate(test_results, start=1):
        if not isinstance(case, dict):
            continue
        test_case_lines.append(
            "testcase {idx}: input={input} expected={expected} "
            "actual={actual} passed={passed}".format(
                idx=index,
                input=case.get("input"),
                expected=case.get("expected_output"),
                actual=case.get("actual_output"),
                passed=case.get("passed"),
            )
        )

    return "\n".join(
        [
            f"compiled_ok: {compilation.get('success')}",
            "compile_errors:",
            _coerce_lines(compilation.get("errors")),
            "runtime_errors:",
            _coerce_lines(execution.get("errors")),
            "runtime_output:",
            "\n".join(output_lines),
            "test_case_results:",
            "\n".join(test_case_lines),
        ]
    ).strip()


def _payload_inputs_from_raw(raw_payload: str) -> dict | None:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    transcribed_text = payload.get("transcribed_text")
    rubric_json = payload.get("rubric_json")
    sandbox_result = payload.get("sandbox_result")

    if transcribed_text is None and rubric_json is None and sandbox_result is None:
        return None

    logs = _format_sandbox_logs(sandbox_result)
    return {
        "code": transcribed_text or "",
        "rubric": rubric_json or {},
        "logs": logs,
    }


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
            "DB adapter is placeholder; cannot run worker until adapter "
            "mapping is configured."
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
            outcome: dict | None = None
            try:
                payload_inputs = _payload_inputs_from_raw(job.raw_payload)
                outcome = await process_submission(
                    submission_id=job.submission_id,
                    db_adapter=db_adapter,
                    llm_client=llm_client,
                    settings=settings,
                    payload_inputs=payload_inputs,
                )
            except Exception as exc:
                logger.exception(
                    "Unhandled worker error while processing submission_id=%s",
                    job.submission_id,
                )
                outcome = {"status": "FAILED", "error": str(exc)}
            finally:
                if job.job_id:
                    completion_payload = _build_completion_payload(
                        job=job,
                        outcome=outcome or {"status": "FAILED"},
                    )
                    try:
                        await queue_adapter.push(
                            f"{settings.ready_queue_name}:completed:{job.job_id}",
                            json.dumps(completion_payload),
                        )
                    except Exception:
                        logger.exception(
                            "Failed to publish AI grading completion for job_id=%s",
                            job.job_id,
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
