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
    logs: str,
    rubric: Any,
    schema: dict[str, Any],
) -> str:
    """
    assembles the main grading prompt - we can change it later
    Sections are:
        role declaration
        task description
        hard requirements (no markdown, cite evidence, do not invent tests)
        the required JSON schema
        the submission_id
        the rubric
        the student code wrapped in BEGIN/END_CODE tags
        sandbox logs wrapped in BEGIN/END_LOGS tags
    it should prevent the model from confusing content with instructions
    Returns: str
    """
    rubric_text = _as_json_block(rubric)
    schema_text = _as_json_block(schema)

    return (
        "Role: Expert Java Grader\n"
        "Task: Assess the following code based on the logs and rubric.\n\n"
        "Hard requirements:\n"
        "- Return ONLY valid JSON matching schema; no markdown; no extra text.\n"
        "- Include rubric criteria and point values in your grading decisions.\n"
        "- Do not invent tests.\n"
        "- Cite concrete evidence from the student code and sandbox logs.\n"
        "- If uncertain, lower confidence and explain uncertainty in "
        "error_classification.notes.\n\n"
        "Required JSON schema:\n"
        f"{schema_text}\n\n"
        f"submission_id: {submission_id}\n\n"
        "Rubric criteria and points (verbatim):\n"
        f"{rubric_text}\n\n"
        "Student code (verbatim):\n"
        "<BEGIN_CODE>\n"
        f"{code}\n"
        "<END_CODE>\n\n"
        "Sandbox compile/run logs (verbatim):\n"
        "<BEGIN_LOGS>\n"
        f"{logs}\n"
        "<END_LOGS>\n"
    )


def construct_output_repair_prompt(
    *,
    submission_id: int,
    previous_output: str,
    schema: dict[str, Any],
) -> str:
    """
    Builds a shorter follow-up prompt sent when the first LLM output
    fails JSON/schema validation.
    This repairs the model output, not prompt construction.
    Includes submission_id, required schema, and previous invalid output so
    the model can self-correct and return complete valid JSON.
    Returns: str
    """
    schema_text = _as_json_block(schema)

    return (
        "The previous response was invalid.\n"
        "Return ONLY valid JSON matching schema; no markdown; no extra text.\n"
        "Do not omit required keys.\n"
        f"Use submission_id={submission_id}.\n\n"
        "Required JSON schema:\n"
        f"{schema_text}\n\n"
        "Previous invalid output:\n"
        "<BEGIN_PREVIOUS_OUTPUT>\n"
        f"{previous_output}\n"
        "<END_PREVIOUS_OUTPUT>\n"
    )
