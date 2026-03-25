"""
OCR job processing logic.

Mirrors the sandbox component's jobs.py pattern:
- Each step (OCR, LLM, flag detection) is a separate function
- Each step mutates the job and returns it (or None on failure)
- The worker orchestrates the step sequence

Step sequence:
    1. ocr_job()     — Azure OCR extraction
    2. correct_job() — Gemini LLM correction + uncertain word detection
    3. flag_job()    — Build flags from LLM's uncertain words
"""

import asyncio
import logging

from settings import settings

from .helpers import correct_ocr, detect_flags, extract_words
from .schemas import (
    FlagDetectionResult,
    JobStatus,
    LLMCorrectionResult,
    OCRExtractionResult,
    OCRJob,
    OCRJobResult,
    OCRResult,
)

logger = logging.getLogger(__name__)


async def ocr_job(job: OCRJob) -> OCRJob | None:
    """
    Step 1: Run Azure OCR extraction on the image.

    Returns the job with ocr_result populated, or None on failure.
    """
    try:
        ocr_lines = await asyncio.to_thread(extract_words, job.request.image_path)

        if not ocr_lines:
            logger.error(
                "OCR returned no text for Job %s",
                job.job_id,
            )
            job.result = OCRResult(
                ocr_result=OCRExtractionResult(
                    success=False,
                    errors=["Azure OCR returned no text."],
                ),
            )
            return None

        raw_text = "\n".join(line.plain_text() for line in ocr_lines)
        annotated_text = "\n".join(line.annotated() for line in ocr_lines)

        job.result = OCRResult(
            ocr_result=OCRExtractionResult(
                success=True,
                raw_text=raw_text,
                annotated_text=annotated_text,
                lines=ocr_lines,
            ),
        )
        logger.info("Job %s OCR extraction successful", job.job_id)
        return job

    except FileNotFoundError as exc:
        logger.error("File error for Job %s: %s", job.job_id, exc)
        job.result = OCRResult(
            ocr_result=OCRExtractionResult(
                success=False,
                errors=[str(exc)],
            ),
        )
        return None

    except Exception as exc:
        logger.error("OCR error for Job %s: %s", job.job_id, exc)
        job.result = OCRResult(
            ocr_result=OCRExtractionResult(
                success=False,
                errors=[f"Azure OCR failed: {exc}"],
            ),
        )
        return None


async def correct_job(job: OCRJob) -> OCRJob | None:
    """
    Step 2: Run Gemini LLM correction on the OCR output.

    The LLM returns:
    - Corrected code (uncertain words left as-is)
    - A list of uncertain words with 5 ranked suggestions each

    Requires ocr_job() to have succeeded first.
    Returns the job with llm_result populated, or None on failure.
    """
    ocr_lines = job.result.ocr_result.lines
    if not ocr_lines:
        logger.error("Job %s has no OCR lines to correct", job.job_id)
        job.result.llm_result = LLMCorrectionResult(
            success=False,
            errors=["No OCR lines available for correction."],
        )
        return None

    annotated_lines = [line.annotated() for line in ocr_lines]

    try:
        corrected_code, uncertain_words = await asyncio.to_thread(
            correct_ocr, annotated_lines
        )

        job.result.llm_result = LLMCorrectionResult(
            success=True,
            corrected_code=corrected_code,
            model_used=settings.gemini_model,
            uncertain_words=(uncertain_words if uncertain_words else None),
        )
        logger.info(
            "Job %s LLM correction successful " "(%d uncertain word(s))",
            job.job_id,
            len(uncertain_words),
        )
        return job

    except RuntimeError as exc:
        logger.error(
            "LLM error for Job %s: %s",
            job.job_id,
            exc,
        )
        job.result.llm_result = LLMCorrectionResult(
            success=False,
            errors=[str(exc)],
        )
        return None

    except Exception as exc:
        logger.error(
            "LLM unexpected error for Job %s: %s",
            job.job_id,
            exc,
        )
        job.result.llm_result = LLMCorrectionResult(
            success=False,
            errors=[f"LLM correction failed: {exc}"],
        )
        return None


def flag_job(job: OCRJob) -> OCRJob:
    """
    Step 3: Build flags from the LLM's uncertain words.

    Uses the uncertain_words list from the LLM response
    (words it could not confidently correct) and creates
    ConfidenceFlag-compatible records with the 5 suggestions.

    Always returns the job (flag detection is non-blocking).
    """
    ocr_lines = job.result.ocr_result.lines or []
    uncertain_words = job.result.llm_result.uncertain_words or []

    try:
        flags = detect_flags(ocr_lines, uncertain_words)

        job.result.flag_result = FlagDetectionResult(
            flags=flags if flags else None,
            flag_count=len(flags),
        )
        logger.info(
            "Job %s flag detection: %d flag(s)",
            job.job_id,
            len(flags),
        )

    except Exception as exc:
        logger.warning(
            "Flag detection failed for Job %s: %s " "(non-blocking, continuing)",
            job.job_id,
            exc,
        )
        job.result.flag_result = FlagDetectionResult(
            flags=None,
            flag_count=0,
        )

    return job


async def set_result(
    job: OCRJob,
    status: JobStatus,
) -> OCRJobResult:
    """Package the final job result for Redis."""
    return OCRJobResult(
        job_id=job.job_id,
        status=status,
        submission_id=job.request.submission_id,
        transcription_id=job.request.transcription_id,
        result=job.result,
    )
