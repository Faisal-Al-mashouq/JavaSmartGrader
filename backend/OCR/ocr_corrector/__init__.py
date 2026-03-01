"""
ocr_corrector — Handwritten Java OCR Correction Pipeline.

Uses Azure Document Intelligence for word-level OCR with confidence
scores, then applies Gemini LLM post-processing to correct machine
misreads while preserving the student's original logic.

Quick start::

    from ocr_corrector import OCRCorrectionPipeline

    result = OCRCorrectionPipeline().run("exam_scan.jpg")
    print(result.corrected_code)
"""

from ocr_corrector.pipeline import OCRCorrectionPipeline
from ocr_corrector.models import CorrectionResult, OCRLine, OCRWord

__all__ = [
    "OCRCorrectionPipeline",
    "CorrectionResult",
    "OCRLine",
    "OCRWord",
]
__version__ = "1.0.0"
