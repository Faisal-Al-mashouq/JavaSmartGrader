from decimal import Decimal

from pydantic import BaseModel


class ConfidenceFlagBase(BaseModel):
    id: int
    transcription_id: int
    text_segment: str
    confidence_score: Decimal
    coordinates: str | None = None
    suggestions: str | None = None

    model_config = {"from_attributes": True}


class ResolveFlagRequest(BaseModel):
    suggestion: str
