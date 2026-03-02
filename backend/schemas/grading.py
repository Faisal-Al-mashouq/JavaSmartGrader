from datetime import datetime

from pydantic import BaseModel


class TranscriptionBase(BaseModel):
    id: int
    submission_id: int
    transcribed_text: str | None

    model_config = {"from_attributes": True}


class CompileResultBase(BaseModel):
    id: int
    submission_id: int
    compiled_ok: bool
    compile_errors: str | None
    runtime_errors: str | None
    runtime_outputs: str | None

    model_config = {"from_attributes": True}


class AIFeedbackBase(BaseModel):
    id: int
    submission_id: int
    suggested_grade: float | None
    instructor_guidance: str | None
    student_feedback: str | None

    model_config = {"from_attributes": True}


class GradeBase(BaseModel):
    id: int
    submission_id: int
    instructor_id: int
    final_grade: float | None
    published_at: datetime | None

    model_config = {"from_attributes": True}
