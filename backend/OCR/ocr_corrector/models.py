"""
Data models for OCR extraction and correction results.

All models use dataclasses with ``to_dict()`` methods for easy
serialization into Redis job payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OCRWord:
    """A single word extracted by Azure OCR."""

    content: str
    confidence: float

    @property
    def confidence_pct(self) -> int:
        return int(self.confidence * 100)

    def __str__(self) -> str:
        return f"{self.content}[{self.confidence_pct}]"

    def to_dict(self) -> dict:
        return {"content": self.content, "confidence": self.confidence}


@dataclass
class OCRLine:
    """A line of OCR words with confidence annotations."""

    words: list[OCRWord] = field(default_factory=list)

    @property
    def annotated(self) -> str:
        """Format: ``public[99] static[98] void[45]``."""
        return " ".join(str(w) for w in self.words)

    @property
    def plain_text(self) -> str:
        return " ".join(w.content for w in self.words)

    def __str__(self) -> str:
        return self.annotated

    def to_dict(self) -> dict:
        return {
            "annotated": self.annotated,
            "plain_text": self.plain_text,
            "words": [w.to_dict() for w in self.words],
        }


@dataclass
class CorrectionResult:
    """
    Final output of the OCR correction pipeline.

    Designed to be fully serializable for Redis job results.
    """

    image_path: str
    ocr_lines: list[OCRLine] = field(default_factory=list)
    raw_ocr_text: str = ""
    corrected_code: str = ""
    model_used: str = ""
    status: str = "pending"  # pending | processing | completed | failed
    error: str | None = None

    @property
    def annotated_text(self) -> str:
        return "\n".join(line.annotated for line in self.ocr_lines)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for Redis / JSON storage."""
        return {
            "image_path": self.image_path,
            "raw_ocr_text": self.raw_ocr_text,
            "annotated_text": self.annotated_text,
            "corrected_code": self.corrected_code,
            "model_used": self.model_used,
            "status": self.status,
            "error": self.error,
        }
