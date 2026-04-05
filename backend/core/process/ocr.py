import re
from collections.abc import Iterator
from datetime import datetime

from db.crud.confidence_flags import create_confidence_flag
from db.crud.grading import create_transcription, get_transcription_by_submission_id
from db.crud.submissions import get_submission_by_id
from db.session import async_session
from ocr.ocr_corrector.schemas import OCRJobRequest, OCRJobResult
from pydantic import ValidationError
from schemas import (
    Job,
    JobRequestPayload,
    JobResultPayload,
    JobStatus,
    JobType,
    OCRPayload,
    OCRResult,
)
from settings import settings

from ..config import JobQueue, logger

OCR_QUEUE = f"{settings.queue_namespace}:{settings.ocr_queue}"


def _normalize_line_leading_public(java_code: str) -> str:
    """Match sandbox: OCR often emits ``Public`` at line start; invalid Java."""
    if not java_code:
        return java_code
    return re.sub(r"(?m)^(\s*)Public(\s+)", r"\1public\2", java_code)


def iter_ocr_job_results(job: Job) -> Iterator[OCRJobResult]:
    """Yield OCR worker results from the job, tolerating union / dict shapes."""
    for p in job.job_result_payload:
        jr = p.job_result
        if jr is None:
            continue
        if isinstance(jr, OCRResult):
            yield jr.result
            continue
        if isinstance(jr, OCRJobResult):
            yield jr
            continue
        if isinstance(jr, dict):
            t = jr.get("type")
            if t not in (JobType.OCR, "OCR"):
                continue
            inner = jr.get("result")
            if isinstance(inner, dict):
                try:
                    yield OCRJobResult.model_validate(inner)
                except ValidationError:
                    continue
            elif isinstance(inner, OCRJobResult):
                yield inner


def _pipeline_best_text(ocr_job_result: OCRJobResult) -> str | None:
    """Prefer non-empty LLM corrected_code, else Azure raw_text."""
    pipeline = ocr_job_result.result
    if not pipeline:
        return None
    llm = pipeline.llm_result
    if llm and llm.corrected_code and str(llm.corrected_code).strip():
        return str(llm.corrected_code).strip()
    ocr_ex = pipeline.ocr_result
    if ocr_ex and ocr_ex.raw_text and str(ocr_ex.raw_text).strip():
        return str(ocr_ex.raw_text).strip()
    if ocr_ex and ocr_ex.lines:
        plain = "\n".join(line.plain_text() for line in ocr_ex.lines)
        if plain.strip():
            return plain.strip()
    return None


def ocr_corrected_text(job: Job) -> str | None:
    """Best available source text after OCR: non-empty LLM-corrected, else raw OCR."""
    for ojr in iter_ocr_job_results(job):
        text = _pipeline_best_text(ojr)
        if text:
            return text
    return None


async def resolve_java_code_for_job(job: Job) -> str:
    """
    Code string for sandbox / grader: in-memory OCR, then typed java_code, then DB transcription.
    """
    t = ocr_corrected_text(job)
    if t:
        return _normalize_line_leading_public(t)
    initial = (job.initial_request.java_code or "").strip()
    if initial:
        return _normalize_line_leading_public(initial)
    async with async_session() as session:
        row = await get_transcription_by_submission_id(
            session, job.initial_request.submission_id
        )
        if row and row.transcribed_text and str(row.transcribed_text).strip():
            return _normalize_line_leading_public(str(row.transcribed_text).strip())
    return ""


async def process_ocr_job(client: JobQueue, job: Job) -> Job | None:
    try:
        logger.debug("Processing OCR Job: %s", job.job_id)
        job.status = JobStatus.RUNNING

        ocr_payload = OCRPayload(
            type=JobType.OCR,
            job_id=job.job_id,
            image_url=job.initial_request.image_url,
        )
        job.job_request_payload.append(
            JobRequestPayload(
                job_payload=ocr_payload,
                created_at=datetime.now(),
            )
        )

        ocr_job_request = OCRJobRequest(
            job_id=job.job_id,
            image_path=job.initial_request.image_url,
        )
        await client.redis_client.lpush(OCR_QUEUE, ocr_job_request.model_dump_json())
        logger.debug("OCR Job %s pushed to %s", job.job_id, OCR_QUEUE)

        _, raw_result = await client.redis_client.brpop(
            f"{OCR_QUEUE}:completed:{job.job_id}", timeout=0
        )
        if not raw_result:
            logger.error("OCR Job %s: no result received from queue", job.job_id)
            return None

        ocr_job_result = OCRJobResult.model_validate_json(raw_result)

        job.job_result_payload.append(
            JobResultPayload(
                job_result=OCRResult(result=ocr_job_result),
                finished_at=datetime.now(),
            )
        )
        job.status = JobStatus.PENDING
        logger.debug("OCR Job %s result received", job.job_id)

        if not await save_to_db(job):
            logger.error("Failed to save OCR Job %s to database", job.job_id)
            return None

        return job
    except Exception as e:
        logger.error("Failed to process OCR Job %s: %s", job.job_id, e)
        return None


async def save_to_db(job: Job) -> bool:
    try:
        async with async_session() as session:
            logger.debug("Saving OCR Job %s to database", job.job_id)

            ocr_job_result = next(iter_ocr_job_results(job), None)
            if not ocr_job_result:
                logger.error("OCR result payload not found for job %s", job.job_id)
                return False
            corrected_text = ocr_corrected_text(job)

            sub_row = await get_submission_by_id(
                session, job.initial_request.submission_id
            )
            if not sub_row:
                logger.error(
                    "Submission %d not found for OCR save; skipping transcription "
                    "(stale MAIN_QUEUE job or wrong DB). Flush Redis queue if needed.",
                    job.initial_request.submission_id,
                )
                return False

            transcription = await create_transcription(
                session=session,
                submission_id=job.initial_request.submission_id,
                transcribed_text=corrected_text,
            )

            flags = []
            if ocr_job_result.result and ocr_job_result.result.flag_result:
                flags = ocr_job_result.result.flag_result.flags or []

            for flag in flags:
                await create_confidence_flag(
                    session=session,
                    transcription_id=transcription.id,
                    text_segment=flag.text_segment,
                    confidence_score=flag.confidence_score,
                    coordinates=flag.coordinates,
                    suggestions=flag.suggestions,
                )

            logger.info(
                "OCR Job %s: transcription saved (id=%d), %d flag(s) persisted",
                job.job_id,
                transcription.id,
                len(flags),
            )
            return True
    except Exception as e:
        logger.error("Failed to save OCR Job %s to database: %s", job.job_id, e)
        return False
