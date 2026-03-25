"""
Helper functions for the OCR correction pipeline.

Contains the core logic for:
- Azure Document Intelligence OCR extraction
- Gemini LLM-based OCR correction
- Low-confidence word flag detection

Mirrors the sandbox component's helpers.py pattern — pure
functions that jobs.py orchestrates.
"""

import logging
from decimal import Decimal
from pathlib import Path

from azure.ai.formrecognizer import (
    AnalysisFeature,
    DocumentAnalysisClient,
)
from azure.core.credentials import AzureKeyCredential
from google import genai
from settings import settings

from .prompts import build_correction_prompt
from .schemas import LLMUncertainWord, OCRFlag, OCRLine, OCRWord

logger = logging.getLogger(__name__)

FLAG_CONFIDENCE_THRESHOLD = 0.30  # 30%


# ── Azure OCR ────────────────────────────────────────────────────


def _build_ocr_client() -> DocumentAnalysisClient:
    return DocumentAnalysisClient(
        endpoint=settings.azure_endpoint,
        credential=AzureKeyCredential(settings.azure_key),
    )


def extract_words(image_path: str) -> list[OCRLine]:
    """
    Analyze an image with Azure high-resolution OCR.

    Parameters
    ----------
    image_path : str
        Path to the image file (JPEG, PNG, TIFF, or PDF).

    Returns
    -------
    list[OCRLine]
        Each element is one line of annotated words.

    Raises
    ------
    FileNotFoundError
        If the image file does not exist.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    logger.info(
        "Analyzing '%s' with Azure high-res layout...",
        path.name,
    )
    client = _build_ocr_client()

    with open(path, "rb") as f:
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

            line_words = [
                OCRWord(
                    content=w.content,
                    confidence=w.confidence,
                )
                for w in page.words
                if w.span.offset >= line_start
                and (w.span.offset + w.span.length) <= line_end
            ]

            if line_words:
                ocr_line = OCRLine(words=line_words)
                lines.append(ocr_line)
                logger.debug("OCR | %s", ocr_line.annotated())

    logger.info(
        "Extracted %d lines from '%s'.",
        len(lines),
        path.name,
    )
    return lines


# ── Gemini LLM Correction ───────────────────────────────────────


def _build_llm_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_key)


def correct_ocr(
    annotated_lines: list[str],
    model: str | None = None,
) -> tuple[str, list[LLMUncertainWord]]:
    """
    Send annotated OCR lines to Gemini for correction.

    The LLM returns two sections:
    1. Corrected code (uncertain words left as-is)
    2. Uncertain words with 5 ranked suggestions each

    Parameters
    ----------
    annotated_lines : list[str]
        Lines in ``word[confidence]`` format.
    model : str, optional
        Override the default Gemini model.

    Returns
    -------
    tuple[str, list[LLMUncertainWord]]
        (corrected_code, uncertain_words)

    Raises
    ------
    RuntimeError
        If the Gemini API call fails.
    """
    model_name = model or settings.gemini_model
    prompt = build_correction_prompt(annotated_lines)

    logger.info(
        "Sending %d lines to %s...",
        len(annotated_lines),
        model_name,
    )

    client = _build_llm_client()
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        raw_response = response.text.strip()
        logger.info(
            "LLM returned %d chars of response.",
            len(raw_response),
        )

        corrected_code, uncertain_words = _parse_llm_response(raw_response)

        logger.info(
            "Parsed: %d chars of code, %d uncertain word(s).",
            len(corrected_code),
            len(uncertain_words),
        )
        return corrected_code, uncertain_words

    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        raise RuntimeError(f"Gemini API failed: {exc}") from exc


def _parse_llm_response(
    raw_response: str,
) -> tuple[str, list[LLMUncertainWord]]:
    """
    Parse the two-section LLM response.

    Expected format::

        ### CORRECTED CODE
        public class Term {
        ...

        ### UNCERTAIN WORDS
        5 | 12 | line:0:word:3 | {, (, [, E, 5

    Returns
    -------
    tuple[str, list[LLMUncertainWord]]
    """
    corrected_code = ""
    uncertain_words: list[LLMUncertainWord] = []

    # Split on the two section headers
    code_marker = "### CORRECTED CODE"
    uncertain_marker = "### UNCERTAIN WORDS"

    # Normalize: strip any leading/trailing whitespace
    text = raw_response.strip()

    # Find section boundaries
    code_start = text.find(code_marker)
    uncertain_start = text.find(uncertain_marker)

    if code_start == -1:
        # No section headers — treat entire response as code
        # (fallback for if LLM ignores the format)
        logger.warning(
            "LLM response missing '### CORRECTED CODE' header. "
            "Treating entire response as corrected code."
        )
        return text, []

    # Extract corrected code section
    code_begin = code_start + len(code_marker)
    code_end = uncertain_start if uncertain_start != -1 else len(text)
    corrected_code = text[code_begin:code_end].strip()

    # Extract uncertain words section
    if uncertain_start != -1:
        uncertain_text = text[uncertain_start + len(uncertain_marker) :].strip()

        if uncertain_text.upper() != "NONE":
            uncertain_words = _parse_uncertain_words(uncertain_text)

    return corrected_code, uncertain_words


def _parse_uncertain_words(
    section_text: str,
) -> list[LLMUncertainWord]:
    """
    Parse the UNCERTAIN WORDS section lines.

    Expected line format::
        original_word | confidence% | line:L:word:W | s1, s2, s3, s4, s5

    Robust: skips malformed lines rather than crashing.
    """
    words: list[LLMUncertainWord] = []

    for line in section_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            logger.warning(
                "Skipping malformed uncertain word line: '%s'",
                line,
            )
            continue

        try:
            original_word = parts[0]
            confidence_pct = int(parts[1].replace("%", "").strip())
            coordinates = parts[2].strip()
            suggestions = [s.strip() for s in parts[3].split(",") if s.strip()]

            # Ensure exactly 5 suggestions (pad or trim)
            suggestions = suggestions[:5]

            words.append(
                LLMUncertainWord(
                    original_word=original_word,
                    confidence_pct=confidence_pct,
                    coordinates=coordinates,
                    suggestions=suggestions,
                )
            )

        except (ValueError, IndexError) as exc:
            logger.warning(
                "Failed to parse uncertain word line " "'%s': %s",
                line,
                exc,
            )
            continue

    return words


# ── Flag Detection ───────────────────────────────────────────────


def detect_flags(
    ocr_lines: list[OCRLine],
    uncertain_words: list[LLMUncertainWord],
) -> list[OCRFlag]:
    """
    Build flags from the LLM's uncertain words list.

    Each uncertain word reported by the LLM becomes a flag
    with the 5 suggestions stored as a comma-separated string
    in the ``suggestions`` field (matching ConfidenceFlag DB).

    The confidence_score is looked up from the original OCR
    lines for precision (the LLM's reported % is a fallback).

    Parameters
    ----------
    ocr_lines : list[OCRLine]
        Original OCR extraction with confidence scores.
    uncertain_words : list[LLMUncertainWord]
        Uncertain words identified by the LLM.

    Returns
    -------
    list[OCRFlag]
        Flags ready for ConfidenceFlag DB persistence.
    """
    flags: list[OCRFlag] = []

    for uw in uncertain_words:
        # Try to get the real confidence from OCR lines
        real_confidence = _lookup_confidence(ocr_lines, uw.coordinates)
        if real_confidence is None:
            # Fallback to the LLM-reported confidence
            real_confidence = uw.confidence_pct / 100.0

        # Format suggestions as comma-separated string
        suggestions_str = ", ".join(uw.suggestions)

        flags.append(
            OCRFlag(
                text_segment=uw.original_word,
                confidence_score=Decimal(str(round(real_confidence, 4))),
                coordinates=uw.coordinates,
                suggestions=suggestions_str,
            )
        )
        logger.debug(
            "Flag: '%s' (conf=%.0f%%, pos=%s) " "suggestions=[%s]",
            uw.original_word,
            real_confidence * 100,
            uw.coordinates,
            suggestions_str,
        )

    logger.info(
        "Flag detection complete: %d word(s) flagged.",
        len(flags),
    )
    return flags


def _lookup_confidence(
    ocr_lines: list[OCRLine],
    coordinates: str,
) -> float | None:
    """
    Look up the real Azure OCR confidence from coordinates.

    Parses "line:L:word:W" and indexes into ocr_lines.
    Returns None if coordinates are invalid or out of bounds.
    """
    try:
        parts = coordinates.split(":")
        # Expected: ["line", "L", "word", "W"]
        if len(parts) != 4:
            return None
        line_idx = int(parts[1])
        word_idx = int(parts[3])

        if line_idx < len(ocr_lines):
            line = ocr_lines[line_idx]
            if word_idx < len(line.words):
                return line.words[word_idx].confidence
    except (ValueError, IndexError):
        pass
    return None


def _normalize(text: str) -> str:
    """Lowercase and strip for comparison."""
    return text.strip().lower()
