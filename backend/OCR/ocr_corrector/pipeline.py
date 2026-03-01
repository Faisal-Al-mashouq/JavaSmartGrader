"""
OCR correction pipeline.

Orchestrates the full flow: image → Azure OCR → LLM correction → result.
Designed to be stateless so it can be invoked directly or from a Redis
worker without modification.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ocr_corrector.config import GEMINI_MODEL
from ocr_corrector.models import CorrectionResult
from ocr_corrector.ocr_engine import extract_words
from ocr_corrector.llm_corrector import correct_ocr

logger = logging.getLogger(__name__)


class OCRCorrectionPipeline:
    """
    Stateless pipeline that processes a single image end-to-end.

    Usage
    -----
    Direct call::

        pipeline = OCRCorrectionPipeline()
        result = pipeline.run("exam_scan.jpg")
        print(result.corrected_code)

    From a Redis worker::

        result = OCRCorrectionPipeline().run(job_data["image_path"])
        redis.set(f"ocr:result:{job_id}", json.dumps(result.to_dict()))
    """

    def __init__(self, model: str | None = None):
        self.model = model or GEMINI_MODEL

    def run(self, image_path: str | Path) -> CorrectionResult:
        """
        Execute the full OCR → correction pipeline.

        Parameters
        ----------
        image_path : str or Path
            Path to the handwritten Java code image.

        Returns
        -------
        CorrectionResult
            Fully serializable result with OCR text, corrected code, and status.
        """
        image_path = str(image_path)
        result = CorrectionResult(image_path=image_path, model_used=self.model)

        try:
            result.status = "processing"

            # Step 1: Azure OCR — extract words with confidence scores
            logger.info("Step 1/2 │ Running Azure OCR on '%s'", Path(image_path).name)
            ocr_lines = extract_words(image_path)

            if not ocr_lines:
                result.status = "failed"
                result.error = "Azure OCR returned no text."
                logger.warning("No text extracted from '%s'.", image_path)
                return result

            result.ocr_lines = ocr_lines
            result.raw_ocr_text = "\n".join(line.plain_text for line in ocr_lines)

            # Step 2: LLM correction — fix OCR misreads, preserve student logic
            logger.info("Step 2/2 │ Correcting with %s", self.model)
            annotated = [line.annotated for line in ocr_lines]
            result.corrected_code = correct_ocr(annotated, model=self.model)

            result.status = "completed"
            logger.info("Pipeline complete for '%s'.", Path(image_path).name)

        except FileNotFoundError as exc:
            result.status = "failed"
            result.error = str(exc)
            logger.error("File error: %s", exc)

        except RuntimeError as exc:
            result.status = "failed"
            result.error = str(exc)
            logger.error("LLM error: %s", exc)

        except Exception as exc:
            result.status = "failed"
            result.error = f"Unexpected error: {exc}"
            logger.exception("Unhandled exception in pipeline.")

        return result
