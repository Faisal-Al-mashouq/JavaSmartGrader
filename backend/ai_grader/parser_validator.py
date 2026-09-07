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


def _strip_markdown_fences(raw_text: str) -> str:
    """Remove optional ``` / ```json wrappers from model output."""
    stripped = raw_text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


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


def _coerce_str(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


RUBRIC_ITEM_KEYS = frozenset(
    {
        "criterion_id_or_name",
        "earned_points",
        "max_points",
        "rationale",
        "evidence_from_code_or_logs",
    }
)
ROOT_HOIST_KEYS = (
    "confidence",
    "error_classification",
    "feedback",
    "total_score",
    "max_score",
)


def _is_evidence_key(key: str) -> bool:
    key_norm = key.lower().replace("-", "_")
    return (
        key_norm == "evidence_from_code_or_logs"
        or "evidence_from_code_or_logs" in key_norm
    )


def _hoist_root_fields(source: dict[str, Any], target: dict[str, Any]) -> None:
    for field in ROOT_HOIST_KEYS:
        if field not in source or target.get(field) is not None:
            continue
        value = source[field]
        if field == "feedback" and isinstance(value, str):
            target["feedback"] = {
                "summary": value,
                "issues": [],
                "suggestions": [],
                "next_steps": [],
            }
        else:
            target[field] = value


def _find_nested_rubric_breakdown(
    items: list[Any],
) -> list[dict[str, Any]] | None:
    best: list[dict[str, Any]] | None = None
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get("rubric_breakdown")
        if not isinstance(nested, list) or not nested:
            continue
        deeper = _find_nested_rubric_breakdown(nested)
        candidate = (
            deeper if deeper else [entry for entry in nested if isinstance(entry, dict)]
        )
        if candidate and (best is None or len(candidate) > len(best)):
            best = candidate
    return best


def _unwrap_misplaced_grading_fields(normalized: dict[str, Any]) -> None:
    rubric_breakdown = normalized.get("rubric_breakdown")
    if not isinstance(rubric_breakdown, list):
        return

    for item in rubric_breakdown:
        if isinstance(item, dict):
            _hoist_root_fields(item, normalized)

    nested = _find_nested_rubric_breakdown(rubric_breakdown)
    if nested:
        rubric_breakdown = nested

    cleaned_items: list[dict[str, Any]] = []
    for item in rubric_breakdown:
        if not isinstance(item, dict):
            continue
        item = dict(item)
        _hoist_root_fields(item, normalized)

        for key in list(item.keys()):
            if key in RUBRIC_ITEM_KEYS or _is_evidence_key(key):
                continue
            if key in ROOT_HOIST_KEYS:
                if normalized.get(key) is None:
                    _hoist_root_fields({key: item[key]}, normalized)
            item.pop(key, None)

        cleaned_items.append(item)

    normalized["rubric_breakdown"] = cleaned_items


def _normalize_grading_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Fix common LLM shape mistakes before strict schema validation."""
    normalized = dict(payload)

    _unwrap_misplaced_grading_fields(normalized)

    if "error_classification_notes" in normalized:
        notes = normalized.pop("error_classification_notes")
        error_classification = normalized.get("error_classification")
        if not isinstance(error_classification, dict):
            error_classification = {}
        error_classification = dict(error_classification)
        if notes and not error_classification.get("notes"):
            error_classification["notes"] = _coerce_str(notes)
        normalized["error_classification"] = error_classification

    if normalized.get("confidence") is None:
        feedback_score = normalized.pop("feedback_score", None)
        if feedback_score is not None:
            normalized["confidence"] = feedback_score
    else:
        normalized.pop("feedback_score", None)

    total_score = normalized.get("total_score")
    max_score = normalized.get("max_score")
    if (
        (isinstance(total_score, int) or isinstance(total_score, float))
        and (isinstance(max_score, int) or isinstance(max_score, float))
        and float(max_score) <= 1
        and float(total_score) > float(max_score)
    ):
        scaled_max = float(max_score) * 100
        if float(total_score) <= scaled_max:
            normalized["max_score"] = scaled_max

    feedback = normalized.get("feedback")
    if not isinstance(feedback, dict):
        feedback = {}
    feedback = dict(feedback)
    for field in ("next_steps", "suggestions", "issues", "summary"):
        if field in normalized:
            root_value = normalized.pop(field)
            if field not in feedback or not feedback.get(field):
                feedback[field] = root_value
    normalized["feedback"] = feedback

    rubric_breakdown = normalized.get("rubric_breakdown")
    if isinstance(rubric_breakdown, list):
        fixed_items: list[dict[str, Any]] = []
        for item in rubric_breakdown:
            if not isinstance(item, dict):
                continue
            fixed_item = dict(item)
            fixed_item["criterion_id_or_name"] = _coerce_str(
                fixed_item.get("criterion_id_or_name")
            )

            evidence_key = "evidence_from_code_or_logs"
            if not fixed_item.get(evidence_key):
                for alias in (
                    "evidence",
                    "evidence_from_logs",
                    "code_evidence",
                    "log_evidence",
                    "e_evidence_from_code_or_logs",
                ):
                    if fixed_item.get(alias):
                        fixed_item[evidence_key] = _coerce_str(fixed_item.pop(alias))
                        break

            for key in list(fixed_item.keys()):
                if key == evidence_key:
                    continue
                key_norm = key.lower().replace("-", "_")
                if "evidence_from_code_or_logs" in key_norm or key_norm.endswith(
                    "evidence_from_code_or_logs"
                ):
                    if not fixed_item.get(evidence_key):
                        fixed_item[evidence_key] = _coerce_str(fixed_item.pop(key))
                    else:
                        fixed_item.pop(key)

            if not fixed_item.get(evidence_key):
                fixed_item[evidence_key] = _coerce_str(fixed_item.get("rationale"))
            fixed_items.append(fixed_item)
        normalized["rubric_breakdown"] = fixed_items

    feedback = normalized.get("feedback")
    if isinstance(feedback, dict):
        fixed_feedback = dict(feedback)
        if (
            normalized.get("confidence") is None
            and fixed_feedback.get("confidence") is not None
        ):
            normalized["confidence"] = fixed_feedback.pop("confidence")
        else:
            fixed_feedback.pop("confidence", None)
        issues = fixed_feedback.get("issues")
        if not isinstance(issues, list):
            issues = []
        fixed_feedback["issues"] = issues
        if not fixed_feedback.get("summary"):
            if issues and isinstance(issues[0], dict):
                fixed_feedback["summary"] = str(
                    issues[0].get("description") or "See detailed feedback below."
                )
            else:
                fixed_feedback["summary"] = "Grading completed."
        fixed_feedback.setdefault("suggestions", [])
        fixed_feedback.setdefault("next_steps", [])
        normalized["feedback"] = fixed_feedback

    error_classification = normalized.get("error_classification")
    if not isinstance(error_classification, dict):
        error_classification = {}
    if isinstance(error_classification, dict):
        fixed_ec = dict(error_classification)
        if (
            "handwritten_ocr_suspected" in fixed_ec
            and "handwriting_ocr_suspected" not in fixed_ec
        ):
            fixed_ec["handwriting_ocr_suspected"] = fixed_ec.pop(
                "handwritten_ocr_suspected"
            )
        fixed_ec.setdefault("handwriting_ocr_suspected", False)
        fixed_ec.setdefault("syntax_or_compile", False)
        fixed_ec.setdefault("runtime", False)
        fixed_ec.setdefault("logic", False)
        fixed_ec.setdefault("notes", "")
        normalized["error_classification"] = fixed_ec

    return normalized


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
    normalized = _strip_markdown_fences(raw_text.strip())
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

    try:
        model = GradingResponse.model_validate(_normalize_grading_payload(payload))
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
