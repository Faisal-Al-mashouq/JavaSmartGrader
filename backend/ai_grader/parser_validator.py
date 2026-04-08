from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .schemas import (
    DatasetGradingResponse,
    GradingResponse,
    normalize_dataset_grading_response,
)

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
    return DatasetGradingResponse.model_json_schema()


def _extract_first_json_object(raw_text: str) -> str:
    """
    Extracts the first balanced JSON object from arbitrary text.
    This allows recovery when the model returns extra prose or trailing tokens.
    Raises JSONValidationError when no balanced JSON object can be found.
    """
    stripped = raw_text.strip()
    start = stripped.find("{")
    if start < 0:
        raise JSONValidationError("Invalid JSON: no JSON object found in response")

    depth = 0
    in_string = False
    escaped = False
    end = -1

    for idx, char in enumerate(stripped[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = False
                continue
        else:
            if char == '"':
                in_string = True
                continue
            if char == "{":
                depth += 1
                continue
            if char == "}":
                depth -= 1
                if depth == 0:
                    end = idx
                    break

    if end < 0:
        raise JSONValidationError("Invalid JSON: unbalanced JSON object in response")

    return stripped[start : end + 1]


def parse_and_validate_json(raw_text: str) -> dict[str, Any]:
    """
    three-step validation:
        1. json.loads to check valid JSON (with fallback extraction of the
        first balanced JSON object if extra text is present)
        2. isinstance check that the root is a dict object
        3. GradingResponse.model_validate to enforce all field types, value
        ranges, and constraints.
    Returns a plain dict via model_dump
    note: Raises JSONValidationError on any failure
    """
    normalized = raw_text.strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as exc:
        try:
            candidate = _extract_first_json_object(normalized)
            payload = json.loads(candidate)
        except (JSONValidationError, json.JSONDecodeError):
            raise JSONValidationError(f"Invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise JSONValidationError("JSON must be an object")

    current_error: ValidationError | None = None

    try:
        model = GradingResponse.model_validate(payload)
        return model.model_dump(mode="python")
    except ValidationError as exc:
        current_error = exc

    try:
        dataset_model = DatasetGradingResponse.model_validate(payload)
        normalized = normalize_dataset_grading_response(dataset_model)
        return normalized.model_dump(mode="python")
    except ValidationError as exc:
        raise JSONValidationError(
            "Schema validation failed. "
            f"Current schema error: {current_error}. "
            f"Dataset schema error: {exc}"
        ) from exc


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
