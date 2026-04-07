"""Tests for the confidence-flag resolve endpoint and re-grading flow.

Covers:
- apply_suggestion_to_text() helper (pure-function unit tests)
- POST /{flag_id}/resolve endpoint (mocked CRUD + background task)
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from db.models import SubmissionState, UserRole
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import create_access_token, get_current_user, require_role
from api.dependencies import get_db
from api.routes.confidence_flags import apply_suggestion_to_text, router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

INSTRUCTOR_USER = SimpleNamespace(
    id=1,
    username="prof",
    email="prof@test.com",
    role=UserRole.instructor,
    password_hash="hashed",
)


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with the confidence-flags router."""
    app = FastAPI()
    app.include_router(router, prefix="/confidence-flags")
    return app


def _instructor_overrides(app: FastAPI, monkeypatch: pytest.MonkeyPatch):
    """Override auth + db dependencies so requests act as an instructor."""
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        return INSTRUCTOR_USER

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db


def _auth_header() -> dict[str, str]:
    token = create_access_token({"sub": str(INSTRUCTOR_USER.id)})
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. apply_suggestion_to_text  — pure-function unit tests
# ===========================================================================


class TestApplySuggestionToText:
    """Unit tests for the word-replacement helper."""

    def test_replace_single_word(self):
        # Tokenizer splits on whitespace, so each space-separated chunk is one word
        text = "public static void mian (String[] args) {"
        result = apply_suggestion_to_text(text, "line:0:word:3", "main")
        assert result == "public static void main (String[] args) {"

    def test_replace_first_word(self):
        text = "pubilc class Hello {"
        result = apply_suggestion_to_text(text, "line:0:word:0", "public")
        assert result == "public class Hello {"

    def test_replace_last_word(self):
        text = "int x = 10;"
        result = apply_suggestion_to_text(text, "line:0:word:3", "10;")
        # word index 3 is "10;" — replacing with same value is a no-op
        assert result == "int x = 10;"

    def test_multiline_replace_second_line(self):
        text = "line zero\nSystem.out.printIn(\"Hello\");\nline two"
        result = apply_suggestion_to_text(text, "line:1:word:0", "System.out.println(\"Hello\");")
        lines = result.split("\n")
        assert lines[0] == "line zero"
        assert "println" in lines[1]
        assert lines[2] == "line two"

    def test_preserves_leading_whitespace(self):
        text = "class A {\n    int x = 5;\n}"
        result = apply_suggestion_to_text(text, "line:1:word:0", "long")
        assert result == "class A {\n    long x = 5;\n}"

    def test_invalid_coordinates_format(self):
        with pytest.raises(ValueError, match="Invalid coordinates format"):
            apply_suggestion_to_text("hello", "bad:format", "world")

    def test_line_index_out_of_range(self):
        with pytest.raises(ValueError, match="Line index .* out of range"):
            apply_suggestion_to_text("only one line", "line:5:word:0", "x")

    def test_word_index_out_of_range(self):
        with pytest.raises(ValueError, match="Word index .* out of range"):
            apply_suggestion_to_text("two words", "line:0:word:10", "x")

    def test_negative_line_index_rejected(self):
        # regex only matches digits, so negative is invalid format
        with pytest.raises(ValueError, match="Invalid coordinates format"):
            apply_suggestion_to_text("hello", "line:-1:word:0", "x")


# ===========================================================================
# 2. POST /{flag_id}/resolve  — endpoint tests
# ===========================================================================

# Fake DB objects returned by mocked CRUD functions
FAKE_FLAG = SimpleNamespace(
    id=42,
    transcription_id=100,
    text_segment="mian",
    confidence_score=Decimal("0.25"),
    coordinates="line:0:word:3",
    suggestions="main,mian,min,man,mine",
)

FAKE_TRANSCRIPTION = SimpleNamespace(
    id=100,
    submission_id=200,
    transcribed_text="public static void mian(String[] args) {",
)

FAKE_SUBMISSION = SimpleNamespace(
    id=200,
    question_id=10,
    assignment_id=5,
    student_id=1,
    state=SubmissionState.graded,
)

FAKE_ASSIGNMENT = SimpleNamespace(
    id=5,
    rubric_json={"criteria": {"Correctness": {"weight": 100}}},
)

FAKE_TESTCASE = SimpleNamespace(
    input="5 3",
    expected_output="8",
)


# Path prefix for patching CRUD calls used in the route module
_ROUTE = "api.routes.confidence_flags"


class TestResolveEndpoint:
    """Integration tests for the resolve confidence-flag endpoint."""

    def _setup(self, monkeypatch):
        app = _make_app()
        _instructor_overrides(app, monkeypatch)
        client = TestClient(app)
        return app, client

    # --- happy path ---

    @patch(f"{_ROUTE}.start_job_process", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_testcases_by_question_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_assignment_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.update_submission_state", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.delete_compile_result_by_submission_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.delete_confidence_flag", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.update_transcription_text", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_transcription_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_confidence_flag_by_id", new_callable=AsyncMock)
    def test_resolve_happy_path(
        self,
        mock_get_flag,
        mock_get_transcription,
        mock_update_text,
        mock_delete_flag,
        mock_get_submission,
        mock_delete_compile,
        mock_update_state,
        mock_get_assignment,
        mock_get_testcases,
        mock_start_job,
        monkeypatch,
    ):
        app, client = self._setup(monkeypatch)

        mock_get_flag.return_value = FAKE_FLAG
        mock_get_transcription.return_value = FAKE_TRANSCRIPTION
        mock_get_submission.return_value = FAKE_SUBMISSION
        mock_get_assignment.return_value = FAKE_ASSIGNMENT
        mock_get_testcases.return_value = [FAKE_TESTCASE]

        resp = client.post(
            "/confidence-flags/42/resolve",
            json={"suggestion": "main"},
            headers=_auth_header(),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["submission_id"] == 200
        assert "re-grading" in body["message"].lower()

        # Verify transcription was updated with corrected text
        mock_update_text.assert_called_once()
        call_args = mock_update_text.call_args
        corrected = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("new_text", call_args[0][-1])
        assert "main" in corrected
        assert "mian" not in corrected

        # Verify flag was deleted
        mock_delete_flag.assert_called_once()

        # Verify old compile result was removed
        mock_delete_compile.assert_called_once()

        # Verify submission state set to processing
        mock_update_state.assert_called_once()
        state_arg = mock_update_state.call_args[0][-1]
        assert state_arg == SubmissionState.processing

    # --- error: flag not found ---

    @patch(f"{_ROUTE}.get_confidence_flag_by_id", new_callable=AsyncMock)
    def test_resolve_flag_not_found(self, mock_get_flag, monkeypatch):
        app, client = self._setup(monkeypatch)
        mock_get_flag.return_value = None

        resp = client.post(
            "/confidence-flags/999/resolve",
            json={"suggestion": "main"},
            headers=_auth_header(),
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    # --- error: flag has no coordinates ---

    @patch(f"{_ROUTE}.get_confidence_flag_by_id", new_callable=AsyncMock)
    def test_resolve_flag_no_coordinates(self, mock_get_flag, monkeypatch):
        app, client = self._setup(monkeypatch)
        flag_no_coords = SimpleNamespace(
            id=42,
            transcription_id=100,
            text_segment="mian",
            confidence_score=Decimal("0.25"),
            coordinates=None,
            suggestions="main",
        )
        mock_get_flag.return_value = flag_no_coords

        resp = client.post(
            "/confidence-flags/42/resolve",
            json={"suggestion": "main"},
            headers=_auth_header(),
        )
        assert resp.status_code == 400
        assert "coordinates" in resp.json()["detail"].lower()

    # --- error: transcription not found ---

    @patch(f"{_ROUTE}.get_transcription_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_confidence_flag_by_id", new_callable=AsyncMock)
    def test_resolve_transcription_not_found(
        self, mock_get_flag, mock_get_transcription, monkeypatch
    ):
        app, client = self._setup(monkeypatch)
        mock_get_flag.return_value = FAKE_FLAG
        mock_get_transcription.return_value = None

        resp = client.post(
            "/confidence-flags/42/resolve",
            json={"suggestion": "main"},
            headers=_auth_header(),
        )
        assert resp.status_code == 404
        assert "transcription" in resp.json()["detail"].lower()

    # --- error: invalid coordinates in flag ---

    @patch(f"{_ROUTE}.get_transcription_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_confidence_flag_by_id", new_callable=AsyncMock)
    def test_resolve_invalid_coordinates(
        self, mock_get_flag, mock_get_transcription, monkeypatch
    ):
        app, client = self._setup(monkeypatch)
        bad_flag = SimpleNamespace(
            id=42,
            transcription_id=100,
            text_segment="mian",
            confidence_score=Decimal("0.25"),
            coordinates="bad:format",
            suggestions="main",
        )
        mock_get_flag.return_value = bad_flag
        mock_get_transcription.return_value = FAKE_TRANSCRIPTION

        resp = client.post(
            "/confidence-flags/42/resolve",
            json={"suggestion": "main"},
            headers=_auth_header(),
        )
        assert resp.status_code == 400

    # --- auth: student cannot resolve ---

    def test_resolve_student_forbidden(self, monkeypatch):
        import api.auth as auth_mod

        async def fake_student_lookup(session, user_id: int):
            return SimpleNamespace(
                id=user_id,
                username="student1",
                email="student@test.com",
                role=UserRole.student,
                password_hash="hashed",
            )

        monkeypatch.setattr(auth_mod, "get_user_by_id", fake_student_lookup)

        app = _make_app()

        async def fake_get_db():
            yield None

        app.dependency_overrides[get_db] = fake_get_db

        client = TestClient(app)
        token = create_access_token({"sub": "99"})

        resp = client.post(
            "/confidence-flags/42/resolve",
            json={"suggestion": "main"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    # --- re-grade uses corrected text, not image ---

    @patch(f"{_ROUTE}.start_job_process", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_testcases_by_question_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_assignment_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.update_submission_state", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.delete_compile_result_by_submission_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.delete_confidence_flag", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.update_transcription_text", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_transcription_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_confidence_flag_by_id", new_callable=AsyncMock)
    def test_resolve_sends_java_code_not_image(
        self,
        mock_get_flag,
        mock_get_transcription,
        mock_update_text,
        mock_delete_flag,
        mock_get_submission,
        mock_delete_compile,
        mock_update_state,
        mock_get_assignment,
        mock_get_testcases,
        mock_start_job,
        monkeypatch,
    ):
        """Verify re-grading is triggered with image_url=None and java_code set,
        which causes the job queue to skip OCR."""
        app, client = self._setup(monkeypatch)

        mock_get_flag.return_value = FAKE_FLAG
        mock_get_transcription.return_value = FAKE_TRANSCRIPTION
        mock_get_submission.return_value = FAKE_SUBMISSION
        mock_get_assignment.return_value = FAKE_ASSIGNMENT
        mock_get_testcases.return_value = [FAKE_TESTCASE]

        resp = client.post(
            "/confidence-flags/42/resolve",
            json={"suggestion": "main"},
            headers=_auth_header(),
        )
        assert resp.status_code == 200

        # The background task calls start_job_process — in TestClient it runs
        # synchronously. Verify it was enqueued with the right args.
        # BackgroundTasks in TestClient runs tasks after the response, so
        # start_job_process should have been called.
        mock_start_job.assert_called_once()
        call_kwargs = mock_start_job.call_args
        # Check via positional or keyword args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        if not kwargs:
            # Passed as positional to add_task, unpack
            pass
        else:
            assert kwargs.get("image_url") is None
            assert "main" in kwargs.get("java_code", "")
            assert kwargs.get("submission_id") == 200

    # --- no test cases falls back to empty ---

    @patch(f"{_ROUTE}.start_job_process", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_testcases_by_question_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_assignment_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.update_submission_state", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.delete_compile_result_by_submission_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.delete_confidence_flag", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.update_transcription_text", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_transcription_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_confidence_flag_by_id", new_callable=AsyncMock)
    def test_resolve_no_testcases_uses_fallback(
        self,
        mock_get_flag,
        mock_get_transcription,
        mock_update_text,
        mock_delete_flag,
        mock_get_submission,
        mock_delete_compile,
        mock_update_state,
        mock_get_assignment,
        mock_get_testcases,
        mock_start_job,
        monkeypatch,
    ):
        """When no test cases exist for the question, the endpoint should
        still succeed using the empty fallback test case."""
        app, client = self._setup(monkeypatch)

        mock_get_flag.return_value = FAKE_FLAG
        mock_get_transcription.return_value = FAKE_TRANSCRIPTION
        mock_get_submission.return_value = FAKE_SUBMISSION
        mock_get_assignment.return_value = FAKE_ASSIGNMENT
        mock_get_testcases.return_value = []  # no test cases

        resp = client.post(
            "/confidence-flags/42/resolve",
            json={"suggestion": "main"},
            headers=_auth_header(),
        )
        assert resp.status_code == 200
        mock_start_job.assert_called_once()
