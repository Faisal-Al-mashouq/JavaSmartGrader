from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .schemas import GradingResponse

"""
guards the system against malformed or hallucinated LLM output
every response must pass through here before anything is written to the database
"""


class JSONValidationError(ValueError):
    """Raised when model output is not valid grading JSON"""


"""
returns the JSON Schema dict generated from GradingResponse.model_json_schema()
used to embed the expected schema in both the main prompt and the repair prompt
so the model knows exactly what to return
Returns: dict

"""


def grading_schema() -> dict[str, Any]:
    return GradingResponse.model_json_schema()


def parse_and_validate_json(raw_text: str) -> dict[str, Any]:
    """
    three-step validation:
        1.json.loads to check valid JSON
        2.isinstance check that the root is a dict object
        3.GradingResponse.model_validate to enforce all field types, value
        ranges, and constraints.
    Returns a plain dict via model_dump
    note: Raises JSONValidationError on any failure
    """
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise JSONValidationError(f"Invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise JSONValidationError("JSON must be an object")

    try:
        model = GradingResponse.model_validate(payload)
    except ValidationError as exc:
        raise JSONValidationError(f"Schema validation failed: {exc}") from exc

    return model.model_dump(mode="python")


def validate_submission_id(
    parsed_payload: dict[str, Any],
    expected_submission_id: int,
) -> None:
    """
    Confirms that the submission_id in the LLM's response matches the job
    being processed
    Prevents a mislabelled grade from being saved to the wrong submission
    Raises JSONValidationError on mismatch
    parameters:
        parsed_payload: dict
        expected_submission_id: int

    """
    actual_submission_id = parsed_payload.get("submission_id")
    if actual_submission_id != expected_submission_id:
        raise JSONValidationError(
            "submission_id mismatch: "
            f"expected {expected_submission_id}, got {actual_submission_id}"
        )
