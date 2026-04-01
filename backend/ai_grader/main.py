from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from redis.asyncio import Redis

from .config import Settings, configure_logging, load_settings
from .llm_client import LLMAPIError, LLMClient
from .parser_validator import (
    JSONValidationError,
    grading_schema,
    parse_and_validate_json,
    validate_submission_id,
)
from .prompt_builder import construct_output_repair_prompt, construct_prompt

"""
Queue-first AI grader worker that mirrors sandbox worker methodology:
- claim jobs from Redis queue into :processing via BRPOPLPUSH
- parse/validate one queue payload per job
- run LLM grading flow
- publish completion to :completed:{job_id}
- remove handled payload from :processing
"""

logger = logging.getLogger(__name__)


class AIGraderJobRequest(BaseModel):
    """
    Canonical queue payload consumed by ai_grader worker.
    """

    model_config = ConfigDict(extra="ignore", strict=True)

    job_id: str
    submission_id: int
    transcribed_text: str = ""
    sandbox_result: dict[str, Any] | None = None
    rubric_json: dict[str, Any] = Field(default_factory=dict)


class AIGraderWorker:
    def __init__(
        self,
        *,
        redis_url: str,
        max_concurrency: int,
    ):
        self.max_concurrency = max_concurrency
        self.redis_client = Redis.from_url(url=redis_url, decode_responses=True)


async def _parse_with_single_repair(
    *,
    submission_id: int,
    first_response_text: str,
    llm_client: LLMClient,
) -> tuple[dict, str]:
    """
    Parse first model output; if invalid, issue one repair prompt.
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

    repair_prompt = construct_output_repair_prompt(
        submission_id=submission_id,
        previous_output=first_response_text,
        schema=schema,
    )
    repair_response = await llm_client.call(repair_prompt, submission_id=submission_id)

    parsed = parse_and_validate_json(repair_response.text)
    validate_submission_id(parsed, submission_id)
    return parsed, repair_response.text


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


def initialize_job(raw_payload: str) -> AIGraderJobRequest | None:
    logger.debug("Initializing AI Grader Job Request: %s", raw_payload)
    try:
        decoded = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse AI Grader payload as JSON: %s", exc)
        return None

    if not isinstance(decoded, dict):
        logger.error("AI Grader payload must be a JSON object.")
        return None

    try:
        job = AIGraderJobRequest.model_validate(decoded)
        logger.debug(
            "AI Grader Job initialized successfully: job_id=%s submission_id=%s",
            job.job_id,
            job.submission_id,
        )
        return job
    except ValidationError as exc:
        logger.error("Invalid AI Grader payload schema: %s", exc)
        return None


async def process_submission(
    *,
    job: AIGraderJobRequest,
    llm_client: LLMClient,
) -> dict:
    """
    Stateless per-job grading flow:
    - build prompt from queue payload
    - call LLM
    - validate JSON with one repair attempt
    """
    logger.info("Processing AI grading for submission_id=%s", job.submission_id)

    logs = _format_sandbox_logs(job.sandbox_result)
    schema = grading_schema()
    prompt = construct_prompt(
        submission_id=job.submission_id,
        code=job.transcribed_text,
        logs=logs,
        rubric=job.rubric_json,
        schema=schema,
    )

    try:
        response = await llm_client.call(prompt, submission_id=job.submission_id)
    except LLMAPIError as exc:
        logger.error(
            "LLM call failed for submission_id=%s after retries: %s",
            job.submission_id,
            exc,
        )
        return {"status": "FAILED", "error": str(exc)}

    try:
        parsed, raw_json_used = await _parse_with_single_repair(
            submission_id=job.submission_id,
            first_response_text=response.text,
            llm_client=llm_client,
        )
    except (JSONValidationError, LLMAPIError) as exc:
        logger.error(
            "Could not produce valid grading JSON for submission_id=%s: %s",
            job.submission_id,
            exc,
        )
        return {
            "status": "FAILED",
            "error": str(exc),
            "raw_output": response.text,
        }

    logger.info("AI grading completed for submission_id=%s.", job.submission_id)
    logger.debug(
        "Final JSON payload for submission_id=%s: %s",
        job.submission_id,
        raw_json_used,
    )
    return {
        "status": "COMPLETED",
        "parsed_feedback": parsed,
    }


def _build_completion_payload(
    *,
    job: AIGraderJobRequest,
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


async def process_job(
    *,
    job: AIGraderJobRequest,
    llm_client: LLMClient,
) -> dict:
    try:
        outcome = await process_submission(job=job, llm_client=llm_client)
    except Exception as exc:
        logger.exception(
            "Unhandled worker error while processing submission_id=%s",
            job.submission_id,
        )
        outcome = {"status": "FAILED", "error": str(exc)}

    return _build_completion_payload(job=job, outcome=outcome)


async def main_loop(
    client: AIGraderWorker,
    *,
    settings: Settings,
    llm_client: LLMClient,
    process_id: int = 0,
    once: bool = False,
) -> None:
    queue_name = settings.ready_queue_name
    processing_queue = f"{queue_name}:processing"
    processed_count = 0

    while True:
        try:
            logger.info("Process #%s: Waiting for job in %s...", process_id, queue_name)
            result = await client.redis_client.brpoplpush(
                src=queue_name,
                dst=processing_queue,
                timeout=settings.queue_poll_timeout_s,
            )
        except asyncio.CancelledError:
            logger.debug("Process #%s cancelled. Shutting down...", process_id)
            return

        if result is None:
            if once and processed_count == 0:
                logger.info("No job received from queue '%s'.", queue_name)
                return
            continue

        logger.info("AI Grader Job Received.")
        logger.debug("Details: %s", result)

        initialized_job = initialize_job(result)
        if not initialized_job:
            logger.error("Failed to initialize AI Grader job, skipping")
            await client.redis_client.lrem(processing_queue, 1, result)
            if once:
                return
            continue

        processed_count += 1
        completion_payload = await process_job(
            job=initialized_job,
            llm_client=llm_client,
        )

        completion_published = True
        completion_queue = f"{queue_name}:completed:{initialized_job.job_id}"
        try:
            await client.redis_client.lpush(
                completion_queue,
                json.dumps(completion_payload),
            )
            logger.debug(
                "AI Grader Job: %s result returned successfully",
                initialized_job.job_id,
            )
        except Exception:
            completion_published = False
            logger.exception(
                "Failed to publish AI grading completion for job_id=%s",
                initialized_job.job_id,
            )

        if completion_published:
            await client.redis_client.lrem(processing_queue, 1, result)
        else:
            logger.error(
                "Leaving job_id=%s in processing queue because completion publish "
                "failed.",
                initialized_job.job_id,
            )

        if once:
            logger.info("Processed one job and exiting due to --once.")
            return


async def run_worker(*, settings: Settings, once: bool = False) -> None:
    client = AIGraderWorker(
        redis_url=settings.redis_url,
        max_concurrency=settings.max_concurrency,
    )
    llm_client = LLMClient(settings)

    logger.info(
        "AI Grader worker started. queue=%s redis=%s",
        settings.ready_queue_name,
        settings.redis_url,
    )

    try:
        if once:
            await main_loop(
                client,
                settings=settings,
                llm_client=llm_client,
                process_id=0,
                once=True,
            )
            return

        await asyncio.gather(
            *(
                main_loop(
                    client,
                    settings=settings,
                    llm_client=llm_client,
                    process_id=pid,
                )
                for pid in range(client.max_concurrency)
            )
        )
    finally:
        await client.redis_client.aclose()


async def start() -> None:
    """
    Async entrypoint used by backend lifespan orchestration.
    """
    settings = load_settings()
    await run_worker(settings=settings)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI grading worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one job if available, then exit.",
    )
    return parser.parse_args()


async def start():
    settings = load_settings()
    configure_logging(settings)
    try:
        await run_worker(settings=settings, once=False)
    except KeyboardInterrupt:
        logger.info("AI Grader worker stopped.")


def main() -> int:
    """
    CLI entrypoint.
    """
    args = _parse_args()
    settings = load_settings()
    configure_logging(settings)
    try:
        asyncio.run(run_worker(settings=settings, once=args.once))
        return 0
    except KeyboardInterrupt:
        logger.info("AI Grader worker stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
