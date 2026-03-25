"""
Pydantic models for the OCR correction pipeline.

Mirrors the sandbox component's schema design:
- Pydantic BaseModel for all data (Redis-serializable via model_dump_json)
- JobStatus enum for lifecycle tracking
- Nested result models for OCR, LLM correction, and flagging
"""

import datetime
import enum
import uuid
from decimal import Decimal

from pydantic import BaseModel

# ── Job Status ───────────────────────────────────────────────────


class JobStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ERROR = "ERROR"


# ── OCR Word / Line Models ───────────────────────────────────────


class OCRWord(BaseModel):
    """A single word extracted by Azure OCR."""

    content: str
    confidence: float  # 0.0 – 1.0

    @property
    def confidence_pct(self) -> int:
        return int(self.confidence * 100)

    def annotated(self) -> str:
        return f"{self.content}[{self.confidence_pct}]"


class OCRLine(BaseModel):
    """A line of OCR words with confidence annotations."""

    words: list[OCRWord]

    def annotated(self) -> str:
        """Format: ``public[99] static[98] void[45]``."""
        return " ".join(w.annotated() for w in self.words)

    def plain_text(self) -> str:
        return " ".join(w.content for w in self.words)


# ── Flag Models ──────────────────────────────────────────────────
# Maps directly to the existing ConfidenceFlag DB table.
# Fields match create_confidence_flag() in confidence_flags.py:
#   text_segment, confidence_score, coordinates, suggestions


class OCRFlag(BaseModel):
    """
    A word flagged for manual review.

    Created when Azure OCR confidence < FLAG_THRESHOLD and the
    LLM corrector did not produce a clear correction.

    Field mapping to ConfidenceFlag DB model:
        text_segment     → the OCR-extracted word
        confidence_score → Azure confidence (Decimal, 0.00–1.00)
        coordinates      → "line:{idx}:word:{idx}" position string
        suggestions      → the LLM's correction attempt (if any)
    """

    text_segment: str
    confidence_score: Decimal
    coordinates: str | None = None
    suggestions: str | None = None


# ── OCR Result Models ────────────────────────────────────────────


class OCRExtractionResult(BaseModel):
    """Result of the Azure OCR extraction step."""

    success: bool
    raw_text: str | None = None
    annotated_text: str | None = None
    lines: list[OCRLine] | None = None
    errors: list[str] | None = None


class LLMUncertainWord(BaseModel):
    """
    An uncertain word identified by the LLM.

    Parsed from the '### UNCERTAIN WORDS' section of the
    LLM response. Contains the original word, its position,
    and 5 ranked correction suggestions.
    """

    original_word: str
    confidence_pct: int
    coordinates: str  # "line:L:word:W"
    suggestions: list[str]  # up to 5 ranked suggestions


class LLMCorrectionResult(BaseModel):
    """Result of the Gemini LLM correction step."""

    success: bool
    corrected_code: str | None = None
    model_used: str | None = None
    uncertain_words: list[LLMUncertainWord] | None = None
    errors: list[str] | None = None


class FlagDetectionResult(BaseModel):
    """Result of the low-confidence flag detection step."""

    flags: list[OCRFlag] | None = None
    flag_count: int = 0


class OCRResult(BaseModel):
    """Full pipeline result combining all steps."""

    ocr_result: OCRExtractionResult | None = None
    llm_result: LLMCorrectionResult | None = None
    flag_result: FlagDetectionResult | None = None


# ── Job Request / Job / Job Result ───────────────────────────────


class OCRJobRequest(BaseModel):
    """
    Payload pushed to the Redis queue.

    Matches sandbox pattern: the API layer creates this and
    pushes it as JSON to the OCR job queue.

    transcription_id is needed so the API layer can call
    create_confidence_flag() with the correct FK after
    the job completes.
    """

    job_id: uuid.UUID
    image_path: str
    submission_id: uuid.UUID | None = None
    transcription_id: int | None = None


class OCRJob(BaseModel):
    """Internal job representation during processing."""

    job_id: uuid.UUID
    status: JobStatus
    created_at: datetime.datetime
    request: OCRJobRequest
    result: OCRResult | None = None


class OCRJobResult(BaseModel):
    """
    Final result pushed to Redis completed queue.

    The API layer reads this and for each flag calls:
        create_confidence_flag(
            session=session,
            transcription_id=result.transcription_id,
            text_segment=flag.text_segment,
            confidence_score=flag.confidence_score,
            coordinates=flag.coordinates,
            suggestions=flag.suggestions,
        )
    """

    job_id: uuid.UUID
    status: JobStatus
    submission_id: uuid.UUID | None = None
    transcription_id: int | None = None
    result: OCRResult | None = None
