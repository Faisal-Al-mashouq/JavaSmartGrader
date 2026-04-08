from __future__ import annotations

import re

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
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


class DatasetRubricBreakdownItem(BaseModel):
    """
    Dataset-facing rubric structure used by the fine-tuning corpus.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    max_points: Numeric
    points_awarded: Numeric
    comments: str

    @model_validator(mode="after")
    def _validate_points(self) -> DatasetRubricBreakdownItem:
        max_points = float(self.max_points)
        points_awarded = float(self.points_awarded)
        if max_points < 0:
            raise ValueError("rubric_breakdown.max_points must be >= 0")
        if points_awarded < 0 or points_awarded > max_points:
            raise ValueError(
                "rubric_breakdown.points_awarded must be within 0..max_points"
            )
        return self


class DatasetErrorClassification(BaseModel):
    """
    Dataset-facing error structure used by the fine-tuning corpus.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    handwriting_ocr_suspected: StrictBool
    syntax_or_compile: StrictBool
    runtime: StrictBool
    logic: StrictBool
    issues: list[str] = Field(default_factory=list)


class DatasetGradingResponse(BaseModel):
    """
    Fine-tuning dataset response shape. This is normalized into GradingResponse
    before anything is published to the rest of the system.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    submission_id: StrictInt
    total_score: Numeric
    max_score: Numeric
    rubric_breakdown: list[DatasetRubricBreakdownItem]
    feedback: str
    error_classification: DatasetErrorClassification
    confidence: Numeric

    @model_validator(mode="after")
    def _validate_scores(self) -> DatasetGradingResponse:
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


def _derive_issue_severity(error_classification: DatasetErrorClassification) -> str:
    if error_classification.syntax_or_compile or error_classification.runtime:
        return "high"
    if error_classification.logic:
        return "medium"
    if error_classification.handwriting_ocr_suspected:
        return "low"
    return "medium"


def _split_feedback_text(feedback: str) -> tuple[str, list[str]]:
    stripped = feedback.strip()
    if not stripped:
        return "No feedback provided.", []

    for marker in ("Next step:", "Next steps:"):
        index = stripped.find(marker)
        if index < 0:
            continue
        summary = stripped[:index].strip()
        next_step = stripped[index + len(marker) :].strip()
        next_steps = [next_step] if next_step else []
        return summary or stripped, next_steps

    return stripped, []


def _normalize_feedback(
    feedback: str,
    error_classification: DatasetErrorClassification,
) -> FeedbackPayload:
    summary, next_steps = _split_feedback_text(feedback)
    severity = _derive_issue_severity(error_classification)
    issues = [
        FeedbackIssue(description=issue.strip(), severity=severity)
        for issue in error_classification.issues
        if isinstance(issue, str) and issue.strip()
    ]

    suggestions: list[str] = []
    review_match = re.search(
        r"(For `[^`]+`, .*?)(?=(?:\s+Next step:|\s+Next steps:|$))",
        feedback.strip(),
    )
    if review_match:
        suggestion = review_match.group(1).strip()
        if suggestion and suggestion != summary:
            suggestions.append(suggestion)

    return FeedbackPayload(
        summary=summary,
        issues=issues,
        suggestions=suggestions,
        next_steps=next_steps,
    )


def normalize_dataset_grading_response(
    dataset_payload: DatasetGradingResponse,
) -> GradingResponse:
    comments_to_notes = [
        issue.strip()
        for issue in dataset_payload.error_classification.issues
        if isinstance(issue, str) and issue.strip()
    ]

    normalized = GradingResponse(
        submission_id=dataset_payload.submission_id,
        total_score=dataset_payload.total_score,
        max_score=dataset_payload.max_score,
        rubric_breakdown=[
            RubricBreakdownItem(
                criterion_id_or_name=item.id,
                earned_points=item.points_awarded,
                max_points=item.max_points,
                rationale=item.comments.strip(),
                evidence_from_code_or_logs=item.comments.strip(),
            )
            for item in dataset_payload.rubric_breakdown
        ],
        feedback=_normalize_feedback(
            dataset_payload.feedback,
            dataset_payload.error_classification,
        ),
        error_classification=ErrorClassification(
            handwriting_ocr_suspected=(
                dataset_payload.error_classification.handwriting_ocr_suspected
            ),
            syntax_or_compile=dataset_payload.error_classification.syntax_or_compile,
            runtime=dataset_payload.error_classification.runtime,
            logic=dataset_payload.error_classification.logic,
            notes="; ".join(comments_to_notes),
        ),
        confidence=dataset_payload.confidence,
    )
    return normalized
