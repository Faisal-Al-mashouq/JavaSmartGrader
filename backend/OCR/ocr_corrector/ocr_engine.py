"""
Azure Document Intelligence OCR extraction.

Sends an image to Azure's ``prebuilt-layout`` model with high-resolution
OCR enabled and returns structured ``OCRLine`` objects containing
word-level confidence annotations.
"""

from __future__ import annotations

import logging
from pathlib import Path

from azure.ai.formrecognizer import AnalysisFeature, DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from ocr_corrector.config import AZURE_ENDPOINT, AZURE_KEY
from ocr_corrector.models import OCRLine, OCRWord

logger = logging.getLogger(__name__)


def _build_client() -> DocumentAnalysisClient:
    return DocumentAnalysisClient(
        endpoint=AZURE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_KEY),
    )


def extract_words(image_path: str | Path) -> list[OCRLine]:
    """
    Analyze an image with Azure high-resolution OCR.

    Parameters
    ----------
    image_path : str or Path
        Path to the image file (JPEG, PNG, TIFF, or PDF).

    Returns
    -------
    list[OCRLine]
        Each element is one line of annotated OCR words.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    logger.info("Analyzing '%s' with Azure high-res layout...", image_path.name)
    client = _build_client()

    with open(image_path, "rb") as f:
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            document=f,
            features=[AnalysisFeature.OCR_HIGH_RESOLUTION],
        )
    result = poller.result()

    lines: list[OCRLine] = []

    for page in result.pages:
        for line in page.lines:
            line_start = line.spans[0].offset
            line_end = line_start + line.spans[0].length

            # Find words that belong to this line based on character spans
            line_words = [
                OCRWord(content=w.content, confidence=w.confidence)
                for w in page.words
                if w.span.offset >= line_start
                and (w.span.offset + w.span.length) <= line_end
            ]

            ocr_line = OCRLine(words=line_words)
            lines.append(ocr_line)
            logger.debug("OCR │ %s", ocr_line.annotated)

    logger.info("Extracted %d lines from '%s'.", len(lines), image_path.name)
    return lines
