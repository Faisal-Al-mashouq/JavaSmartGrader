"""
LLM-based OCR correction using Google Gemini.

Takes confidence-annotated OCR lines and sends them to Gemini
for intelligent post-processing that fixes machine misreads
while preserving the student's original logic.
"""

from __future__ import annotations

import logging

from google import genai

from ocr_corrector.config import GEMINI_KEY, GEMINI_MODEL
from ocr_corrector.prompts import build_correction_prompt

logger = logging.getLogger(__name__)


def _build_client() -> genai.Client:
    return genai.Client(api_key=GEMINI_KEY)


def correct_ocr(
    annotated_lines: list[str],
    model: str | None = None,
) -> str:
    """
    Send annotated OCR lines to Gemini and return corrected Java code.

    Parameters
    ----------
    annotated_lines : list[str]
        Lines in ``word[confidence]`` format from Azure OCR.
    model : str, optional
        Override the default Gemini model from config.

    Returns
    -------
    str
        Corrected Java source code.

    Raises
    ------
    RuntimeError
        If the Gemini API call fails.
    """
    model = model or GEMINI_MODEL
    logger.info("Sending %d lines to %s for correction...", len(annotated_lines), model)

    client = _build_client()
    prompt = build_correction_prompt(annotated_lines)

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        corrected = response.text.strip()
        logger.info("Correction complete (%d chars returned).", len(corrected))
        return corrected

    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        raise RuntimeError(f"LLM correction failed: {exc}") from exc
