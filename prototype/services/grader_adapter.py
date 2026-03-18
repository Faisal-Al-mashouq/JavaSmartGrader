from __future__ import annotations

import json
from typing import Any


def _infer_max_score(rubric_payload: Any) -> float:
    if isinstance(rubric_payload, dict):
        direct_max = rubric_payload.get("max_score")
        if isinstance(direct_max, (int, float)):
            return float(direct_max)

        criteria = rubric_payload.get("criteria")
        if isinstance(criteria, list):
            total = 0.0
            for item in criteria:
                if isinstance(item, dict) and isinstance(
                    item.get("points"), (int, float)
                ):
                    total += float(item["points"])
            if total > 0:
                return total
    return 100.0


def grade(code_text: str, rubric_json: str | dict, sandbox_logs: str) -> dict[str, Any]:
    """
    Thin grader adapter.

    Replace this function with your real grader integration.
    Expected output is a JSON-serializable dict containing
    total_score, max_score, rubric_breakdown, and feedback.
    """
    rubric_payload: Any = rubric_json
    if isinstance(rubric_json, str):
        try:
            rubric_payload = json.loads(rubric_json)
        except json.JSONDecodeError:
            rubric_payload = {}

    max_score = _infer_max_score(rubric_payload)
    lowered = code_text.lower()
    logs_lower = sandbox_logs.lower()

    if "demo-level: high" in lowered and "runtime error" not in logs_lower:
        score = round(max_score * 0.92, 2)
        summary = "High-quality submission with strong correctness."
    elif "demo-level: mid" in lowered and "runtime error" not in logs_lower:
        score = round(max_score * 0.67, 2)
        summary = "Partially correct submission with moderate issues."
    elif "runtime error" in logs_lower or "failed" in logs_lower:
        score = round(max_score * 0.28, 2)
        summary = "Low score due to compile/runtime problems."
    else:
        score = round(max_score * 0.58, 2)
        summary = "Average submission with room for improvement."

    rubric_breakdown = [
        {
            "criterion_id_or_name": "Correctness",
            "earned_points": score,
            "max_points": max_score,
            "rationale": summary,
            "evidence_from_code_or_logs": sandbox_logs[:400],
        }
    ]

    return {
        "total_score": score,
        "max_score": max_score,
        "rubric_breakdown": rubric_breakdown,
        "feedback": {
            "summary": summary,
            "issues": [],
            "suggestions": [
                "Improve edge-case handling.",
                "Add targeted tests before submission.",
            ],
            "next_steps": [
                "Review sandbox logs and fix failing behavior.",
            ],
        },
    }
