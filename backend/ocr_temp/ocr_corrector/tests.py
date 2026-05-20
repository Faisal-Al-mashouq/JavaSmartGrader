"""
Unit tests for the OCR corrector pipeline.

These tests validate the internal logic WITHOUT calling
any external APIs (no Azure, no Gemini, no Redis needed).

Run from backend/:
    python -m pytest ocr_corrector/tests.py -v

Or directly:
    python -m ocr_corrector.tests
"""

import sys
from decimal import Decimal

# ── Test 1: LLM Response Parsing ────────────────────────────────


def test_parse_llm_response_normal():
    """Test parsing a well-formed two-section LLM response."""
    from .helpers import _parse_llm_response

    raw = """### CORRECTED CODE
public class Term {
private int b;

### UNCERTAIN WORDS
5 | 12 | line:0:word:3 | {, (, [, E, 5
Ij | 8 | line:1:word:2 | if, If, I, i, lj"""

    code, uncertain = _parse_llm_response(raw)

    assert "public class Term {" in code
    assert "private int b;" in code
    assert len(uncertain) == 2

    # First uncertain word
    assert uncertain[0].original_word == "5"
    assert uncertain[0].confidence_pct == 12
    assert uncertain[0].coordinates == "line:0:word:3"
    assert len(uncertain[0].suggestions) == 5
    assert uncertain[0].suggestions[0] == "{"

    # Second uncertain word
    assert uncertain[1].original_word == "Ij"
    assert uncertain[1].confidence_pct == 8
    assert uncertain[1].coordinates == "line:1:word:2"

    print("  PASS: test_parse_llm_response_normal")


def test_parse_llm_response_no_uncertain():
    """Test parsing when LLM reports no uncertain words."""
    from .helpers import _parse_llm_response

    raw = """### CORRECTED CODE
public class Main {
System.out.println("Hello");
}

### UNCERTAIN WORDS
NONE"""

    code, uncertain = _parse_llm_response(raw)

    assert "public class Main {" in code
    assert len(uncertain) == 0

    print("  PASS: test_parse_llm_response_no_uncertain")


def test_parse_llm_response_fallback():
    """Test fallback when LLM ignores the format entirely."""
    from .helpers import _parse_llm_response

    raw = """public class Main {
System.out.println("Hello");
}"""

    code, uncertain = _parse_llm_response(raw)

    assert "public class Main {" in code
    assert len(uncertain) == 0

    print("  PASS: test_parse_llm_response_fallback")


def test_parse_uncertain_words_malformed():
    """Test that malformed lines are skipped gracefully."""
    from .helpers import _parse_uncertain_words

    section = """5 | 12 | line:0:word:3 | {, (, [, E, 5
this line is garbage
| | |
abc | notanumber | line:1:word:0 | a, b, c
Z | 20 | line:2:word:1 | z, Z, 2, S, s"""

    words = _parse_uncertain_words(section)

    # Only first and last lines should parse
    assert len(words) == 2
    assert words[0].original_word == "5"
    assert words[1].original_word == "Z"

    print("  PASS: test_parse_uncertain_words_malformed")


# ── Test 2: Flag Detection ──────────────────────────────────────


def test_detect_flags_from_uncertain_words():
    """Test that uncertain words become proper OCRFlag objects."""
    from .helpers import detect_flags
    from .schemas import LLMUncertainWord, OCRLine, OCRWord

    # Simulate OCR lines
    ocr_lines = [
        OCRLine(
            words=[
                OCRWord(content="public", confidence=0.95),
                OCRWord(content="class", confidence=0.99),
                OCRWord(content="Term", confidence=0.92),
                OCRWord(content="5", confidence=0.12),
            ]
        ),
        OCRLine(
            words=[
                OCRWord(content="private", confidence=0.88),
                OCRWord(content="int", confidence=0.91),
                OCRWord(content="Ij", confidence=0.08),
            ]
        ),
    ]

    # Simulate LLM uncertain words
    uncertain = [
        LLMUncertainWord(
            original_word="5",
            confidence_pct=12,
            coordinates="line:0:word:3",
            suggestions=["{", "(", "[", "E", "5"],
        ),
        LLMUncertainWord(
            original_word="Ij",
            confidence_pct=8,
            coordinates="line:1:word:2",
            suggestions=["if", "If", "I", "i", "lj"],
        ),
    ]

    flags = detect_flags(ocr_lines, uncertain)

    assert len(flags) == 2

    # Flag 1: '5' with real confidence from OCR
    f1 = flags[0]
    assert f1.text_segment == "5"
    assert f1.confidence_score == Decimal("0.12")
    assert f1.coordinates == "line:0:word:3"
    assert "{" in f1.suggestions
    assert "(" in f1.suggestions

    # Flag 2: 'Ij' with real confidence from OCR
    f2 = flags[1]
    assert f2.text_segment == "Ij"
    assert f2.confidence_score == Decimal("0.08")
    assert f2.coordinates == "line:1:word:2"
    assert "if" in f2.suggestions

    print("  PASS: test_detect_flags_from_uncertain_words")


def test_detect_flags_confidence_lookup_fallback():
    """Test that bad coordinates fall back to LLM confidence."""
    from .helpers import detect_flags
    from .schemas import LLMUncertainWord, OCRLine, OCRWord

    ocr_lines = [
        OCRLine(words=[OCRWord(content="x", confidence=0.50)]),
    ]

    uncertain = [
        LLMUncertainWord(
            original_word="x",
            confidence_pct=25,
            coordinates="line:99:word:99",  # out of bounds
            suggestions=["X", "y", "z", "k", "x"],
        ),
    ]

    flags = detect_flags(ocr_lines, uncertain)

    assert len(flags) == 1
    # Should fall back to LLM-reported 25%
    assert flags[0].confidence_score == Decimal("0.25")

    print("  PASS: test_detect_flags_confidence_lookup_fallback")


# ── Test 3: Schema Serialization ────────────────────────────────


def test_ocr_job_request_json_roundtrip():
    """Test that OCRJobRequest survives JSON serialization."""
    import uuid

    from .schemas import OCRJobRequest

    original = OCRJobRequest(
        job_id=uuid.uuid4(),
        image_path="/uploads/exam_001.jpg",
        submission_id=uuid.uuid4(),
        transcription_id=42,
    )

    # Serialize (what gets pushed to Redis)
    json_str = original.model_dump_json()

    # Deserialize (what the worker reads)
    restored = OCRJobRequest.model_validate_json(json_str)

    assert restored.job_id == original.job_id
    assert restored.image_path == original.image_path
    assert restored.submission_id == original.submission_id
    assert restored.transcription_id == 42

    print("  PASS: test_ocr_job_request_json_roundtrip")


def test_ocr_job_result_json_roundtrip():
    """Test full OCRJobResult with flags survives serialization."""
    import uuid

    from .schemas import (
        FlagDetectionResult,
        JobStatus,
        LLMCorrectionResult,
        LLMUncertainWord,
        OCRExtractionResult,
        OCRFlag,
        OCRJobResult,
        OCRLine,
        OCRResult,
        OCRWord,
    )

    result = OCRJobResult(
        job_id=uuid.uuid4(),
        status=JobStatus.COMPLETED,
        submission_id=uuid.uuid4(),
        transcription_id=42,
        result=OCRResult(
            ocr_result=OCRExtractionResult(
                success=True,
                raw_text="public class Term 5",
                annotated_text="public[95] class[99] Term[92] 5[12]",
                lines=[
                    OCRLine(
                        words=[
                            OCRWord(content="public", confidence=0.95),
                            OCRWord(content="class", confidence=0.99),
                            OCRWord(content="Term", confidence=0.92),
                            OCRWord(content="5", confidence=0.12),
                        ]
                    )
                ],
            ),
            llm_result=LLMCorrectionResult(
                success=True,
                corrected_code="public class Term 5",
                model_used="gemini",
                uncertain_words=[
                    LLMUncertainWord(
                        original_word="5",
                        confidence_pct=12,
                        coordinates="line:0:word:3",
                        suggestions=["{", "(", "[", "E", "5"],
                    )
                ],
            ),
            flag_result=FlagDetectionResult(
                flags=[
                    OCRFlag(
                        text_segment="5",
                        confidence_score=Decimal("0.12"),
                        coordinates="line:0:word:3",
                        suggestions="{, (, [, E, 5",
                    )
                ],
                flag_count=1,
            ),
        ),
    )

    # Serialize -> deserialize
    json_str = result.model_dump_json()
    restored = OCRJobResult.model_validate_json(json_str)

    assert restored.status == JobStatus.COMPLETED
    assert restored.transcription_id == 42
    assert restored.result.flag_result.flag_count == 1
    assert restored.result.flag_result.flags[0].text_segment == "5"
    assert "{" in restored.result.flag_result.flags[0].suggestions
    assert restored.result.llm_result.uncertain_words[0].suggestions[0] == "{"

    print("  PASS: test_ocr_job_result_json_roundtrip")


# ── Test 4: OCRWord / OCRLine Methods ──────────────────────────


def test_ocr_word_annotated():
    """Test OCRWord annotated format."""
    from .schemas import OCRWord

    word = OCRWord(content="public", confidence=0.95)
    assert word.annotated() == "public[95]"
    assert word.confidence_pct == 95

    word2 = OCRWord(content="5", confidence=0.12)
    assert word2.annotated() == "5[12]"

    print("  PASS: test_ocr_word_annotated")


def test_ocr_line_methods():
    """Test OCRLine annotated and plain_text methods."""
    from .schemas import OCRLine, OCRWord

    line = OCRLine(
        words=[
            OCRWord(content="public", confidence=0.95),
            OCRWord(content="class", confidence=0.99),
            OCRWord(content="Term", confidence=0.92),
        ]
    )

    assert line.annotated() == "public[95] class[99] Term[92]"
    assert line.plain_text() == "public class Term"

    print("  PASS: test_ocr_line_methods")


# ── Runner ──────────────────────────────────────────────────────


def run_all_tests():
    tests = [
        test_ocr_word_annotated,
        test_ocr_line_methods,
        test_parse_llm_response_normal,
        test_parse_llm_response_no_uncertain,
        test_parse_llm_response_fallback,
        test_parse_uncertain_words_malformed,
        test_detect_flags_from_uncertain_words,
        test_detect_flags_confidence_lookup_fallback,
        test_ocr_job_request_json_roundtrip,
        test_ocr_job_result_json_roundtrip,
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 50}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
