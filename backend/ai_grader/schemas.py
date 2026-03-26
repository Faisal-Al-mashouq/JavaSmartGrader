from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictBool,
    StrictFloat,
    StrictInt,
    model_validator,
)

"""
defines the exact structure the LLM must return as a set of nested Pydantic models
all models use strict mode (extra='forbid') so unexpected keys from the LLM
cause immediate
validation failure rather than silent data loss
"""
Numeric = StrictInt | StrictFloat


class RubricBreakdownItem(BaseModel):
    """
    validates individual grading criteria, ensuring earned points stay
    within a valid 0-max range
    output: a structured object containing points, rationale, and evidence
    for a specific rubric line item
    how: Uses a Pydantic model with a model_validator to enforce
    mathematical logic on point totals
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    criterion_id_or_name: str
    earned_points: Numeric
    max_points: Numeric
    rationale: str
    evidence_from_code_or_logs: str

    @model_validator(mode="after")
    def _validate_points(self) -> RubricBreakdownItem:
        max_points = float(self.max_points)
        earned_points = float(self.earned_points)
        if max_points < 0:
            raise ValueError("rubric_breakdown.max_points must be >= 0")
        if earned_points < 0 or earned_points > max_points:
            raise ValueError(
                "rubric_breakdown.earned_points must be within 0..max_points"
            )
        return self


class FeedbackIssue(BaseModel):
    """
    What it does: Defines a specific "bug" or "point of interest" found in
    the student's work
    Output: A structured report of a single mistake, including where it
    happened and how bad it is
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    location: str | None = None
    description: str
    severity: str


class FeedbackPayload(BaseModel):
    """
    Acts as the "Teachers Remarks" section, combining the summary, specific
    issues, and advice
    Output: A complete pedagogical package of feedback that can be displayed
    directly to a student
    How: It organizes a list of FeedbackIssue objects and simple strings
    for suggestions and next_steps
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    summary: str
    issues: list[FeedbackIssue]
    suggestions: list[str]
    next_steps: list[str]


class ErrorClassification(BaseModel):
    """
    What it does: Diagnoses the type of failure to help determine why a
    student is struggling
    Output: A "checklist" of error types (Syntax, Logic, Runtime) and extra notes
    How: It forces the LLM to provide strict True/False values for each
    category, preventing vague answers
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    handwriting_ocr_suspected: StrictBool
    syntax_or_compile: StrictBool
    runtime: StrictBool
    logic: StrictBool
    notes: str


class GradingResponse(BaseModel):
    """
    What it does: Serves as the master container that holds the entire
    grading result for one submission
    Output: The final, verified grade, confidence score, and all nested feedback objects
    How: It assembles all previous models and runs a final check on the
    total_score and submission_id
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    submission_id: StrictInt
    total_score: Numeric
    max_score: Numeric
    rubric_breakdown: list[RubricBreakdownItem]
    feedback: FeedbackPayload
    error_classification: ErrorClassification
    confidence: Numeric

    @model_validator(mode="after")
    def _validate_scores(self) -> GradingResponse:
        max_score = float(self.max_score)
        total_score = float(self.total_score)
        confidence = float(self.confidence)

        if self.submission_id <= 0:
            raise ValueError("submission_id must be a positive integer")
        if max_score < 0:
            raise ValueError("max_score must be >= 0")
        if total_score < 0 or total_score > max_score:
            raise ValueError("total_score must be within 0..max_score")
        if confidence < 0 or confidence > 1:
            raise ValueError("confidence must be within 0..1")
        return self
