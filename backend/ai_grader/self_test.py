from __future__ import annotations

import json

from ai_grader.parser_validator import (
    JSONValidationError,
    grading_schema,
    parse_and_validate_json,
    validate_submission_id,
)
from ai_grader.prompt_builder import construct_prompt


def _test_parser_accepts_valid_json() -> None:
    payload = {
        "submission_id": 101,
        "total_score": 8.5,
        "max_score": 10,
        "rubric_breakdown": [
            {
                "criterion_id_or_name": "Compilation",
                "earned_points": 3,
                "max_points": 4,
                "rationale": "One warning but successful compile.",
                "evidence_from_code_or_logs": "compiled_ok: true",
            },
            {
                "criterion_id_or_name": "Correctness",
                "earned_points": 5.5,
                "max_points": 6,
                "rationale": "Output mostly correct except edge input.",
                "evidence_from_code_or_logs": "runtime_output: ...",
            },
        ],
        "feedback": {
            "summary": "Solid attempt with minor edge-case issue.",
            "issues": [
                {
                    "location": "Line 14",
                    "description": "Null input not handled.",
                    "severity": "medium",
                }
            ],
            "suggestions": ["Add null checks before parsing input."],
            "next_steps": ["Run tests with empty and null-like inputs."],
        },
        "error_classification": {
            "handwriting_ocr_suspected": False,
            "syntax_or_compile": False,
            "runtime": False,
            "logic": True,
            "notes": "Edge-case handling appears incomplete.",
        },
        "confidence": 0.81,
    }

    parsed = parse_and_validate_json(json.dumps(payload))
    validate_submission_id(parsed, 101)
    assert float(parsed["total_score"]) == 8.5


def _test_parser_rejects_incomplete_json() -> None:
    bad_json = json.dumps({"submission_id": 3})
    try:
        parse_and_validate_json(bad_json)
    except JSONValidationError:
        return
    raise AssertionError("Expected JSONValidationError for incomplete payload")


def _test_prompt_contains_verbatim_sections() -> None:
    schema = grading_schema()
    prompt = construct_prompt(
        submission_id=42,
        code="class Main { public static void main(String[] args) {} }",
        logs="compiled_ok: true\nruntime_output:\nHello",
        rubric={"criteria": [{"name": "Correctness", "points": 10}]},
        schema=schema,
    )
    assert "Return ONLY valid JSON matching schema" in prompt
    assert "class Main" in prompt
    assert "compiled_ok: true" in prompt
    assert '"Correctness"' in prompt

async def _test_live_llm_call() -> None:
    import os
    api_key = os.getenv("API_KEY", "")
    model = os.getenv("MODEL", "")
    if not api_key or not model:
        print("Skipping live LLM test: API_KEY or MODEL not set.")
        return

    from ai_grader.config import load_settings
    from ai_grader.llm_client import LLMClient

    settings = load_settings()
    client = LLMClient(settings)

    schema = grading_schema()
    prompt = construct_prompt(
        submission_id=1,
        code="class Main { public static void main(String[] args) { System.out.println(1 + 1); } }",
        logs="compiled_ok: true\nruntime_output:\n2",
        rubric={"criteria": [{"name": "Correctness", "points": 10}]},
        schema=schema,
    )

    response = await client.call(prompt, submission_id=1)
    from ai_grader.parser_validator import parse_and_validate_json, validate_submission_id
    parsed = parse_and_validate_json(response.text)
    validate_submission_id(parsed, 1)
    print(f"Live LLM test passed. Score: {parsed['total_score']}/{parsed['max_score']}")


def run_self_test() -> None:
    import asyncio
    _test_parser_accepts_valid_json()
    _test_parser_rejects_incomplete_json()
    _test_prompt_contains_verbatim_sections()
    asyncio.run(_test_live_llm_call())
    print("ai_grader self-test passed")


if __name__ == "__main__":
    run_self_test()
