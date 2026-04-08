from __future__ import annotations

import json
from typing import Any

"""
Stateless module containing pure prompt-formatting helpers.
It builds:
- the main grading prompt
- an output-repair prompt when prior model output is invalid
No side effects, no I/O.
"""


def _as_json_block(value: Any) -> str:
    """
    Serialises any Python value to a pretty-printed sorted-key, ASCII-safe JSON string
    Used to embed the rubric and JSON schema inside the prompt in a deterministic format
    Returns: str

    """
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True)


def construct_prompt(
    *,
    submission_id: int,
    code: str,
    evaluation: dict[str, Any],
    rubric: Any,
    schema: dict[str, Any],
) -> str:
    """
    Builds the dataset-style user message used by the fine-tuning corpus.
    The main prompt is intentionally just a JSON payload so runtime requests
    match the structure the model saw during training.
    Returns: str
    """
    del schema  # The dataset-style prompt relies on message structure, not prose.

    payload: dict[str, Any] = {
        "submission_id": submission_id,
        "code": code,
        "evaluation": evaluation,
        "rubric": rubric,
    }

    if isinstance(rubric, dict):
        instructor_focus = rubric.get("instructor_focus")
        if isinstance(instructor_focus, str) and instructor_focus.strip():
            payload["instructor_notes"] = instructor_focus.strip()

    return json.dumps(payload, ensure_ascii=True)


def construct_output_repair_prompt(
    *,
    submission_id: int,
    previous_output: str,
    schema: dict[str, Any],
) -> str:
    """
    Builds a shorter follow-up prompt sent when the first LLM output
    fails JSON/schema validation. The repair prompt stays explicit about the
    dataset-facing response contract so the model can self-correct cleanly.
    Returns: str
    """
    schema_text = _as_json_block(schema)

    return (
        "The previous response was invalid.\n"
        "Return ONLY valid JSON matching the required schema. "
        "Do not add markdown.\n"
        "Do not omit required keys.\n"
        f"Use submission_id={submission_id}.\n\n"
        "Required JSON schema:\n"
        f"{schema_text}\n\n"
        "Previous invalid output:\n"
        "<BEGIN_PREVIOUS_OUTPUT>\n"
        f"{previous_output}\n"
        "<END_PREVIOUS_OUTPUT>\n"
    )
