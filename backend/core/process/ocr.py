from datetime import datetime

from db.crud.confidence_flags import create_confidence_flag
from db.crud.grading import create_transcription
from db.session import async_session
from ocr.ocr_corrector.schemas import OCRJobRequest, OCRJobResult
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


def ocr_corrected_text(job: Job) -> str | None:
    """Best available source text after OCR: LLM-corrected, else raw OCR."""
    ocr_wrapped = next(
        (
            p.job_result
            for p in job.job_result_payload
            if p.job_result and getattr(p.job_result, "type", None) == JobType.OCR
        ),
        None,
    )
    if not ocr_wrapped:
        return None
    ocr_job_result: OCRJobResult = ocr_wrapped.result
    if ocr_job_result.result and ocr_job_result.result.llm_result:
        return ocr_job_result.result.llm_result.corrected_code
    if ocr_job_result.result and ocr_job_result.result.ocr_result:
        return ocr_job_result.result.ocr_result.raw_text
    return None


async def process_ocr_job(client: JobQueue, job: Job) -> Job | None:
    try:
        logger.debug("Processing OCR Job: %s", job.job_id)
        job.status = JobStatus.RUNNING

        ocr_payload = OCRPayload(
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

            ocr_payload = next(
                (
                    p.job_result
                    for p in job.job_result_payload
                    if p.job_result
                    and getattr(p.job_result, "type", None) == JobType.OCR
                ),
                None,
            )
            if not ocr_payload:
                logger.error("OCR result payload not found for job %s", job.job_id)
                return False

            ocr_job_result: OCRJobResult = ocr_payload.result
            corrected_text = ocr_corrected_text(job)

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
