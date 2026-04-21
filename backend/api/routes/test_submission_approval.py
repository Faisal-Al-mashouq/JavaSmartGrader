"""Tests for the student-approval endpoints on the submissions router.

Covers:
- GET  /{submission_id}/pending-review
- POST /{submission_id}/approve-transcription
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from db.models import SubmissionState, UserRole
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import create_access_token
from api.dependencies import get_db
from api.routes.submissions import router

STUDENT_USER = SimpleNamespace(
    id=1,
    username="stud",
    email="stud@test.com",
    role=UserRole.student,
    password_hash="hashed",
)

OTHER_STUDENT = SimpleNamespace(
    id=2,
    username="other",
    email="other@test.com",
    role=UserRole.student,
    password_hash="hashed",
)


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/submissions")
    return app


def _student_overrides(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch, user=STUDENT_USER
):
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        return user

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db


def _auth_header(user=STUDENT_USER) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


FAKE_SUBMISSION_AWAITING = SimpleNamespace(
    id=200,
    question_id=10,
    assignment_id=5,
    student_id=STUDENT_USER.id,
    image_url="s3://bucket/img.png",
    state=SubmissionState.awaiting_student_approval,
    submitted_at=datetime.now(UTC),
)

FAKE_SUBMISSION_GRADED = SimpleNamespace(
    id=200,
    question_id=10,
    assignment_id=5,
    student_id=STUDENT_USER.id,
    image_url="s3://bucket/img.png",
    state=SubmissionState.graded,
    submitted_at=datetime.now(UTC),
)

FAKE_TRANSCRIPTION = SimpleNamespace(
    id=100,
    submission_id=200,
    transcribed_text="public static void mian(String[] args) {",
)

FAKE_FLAG = SimpleNamespace(
    id=42,
    transcription_id=100,
    text_segment="mian",
    confidence_score=Decimal("0.25"),
    coordinates="line:0:word:3",
    suggestions="main,mian,min",
)

FAKE_ASSIGNMENT = SimpleNamespace(
    id=5,
    rubric_json={"criteria": {"Correctness": {"weight": 100}}},
)

FAKE_TESTCASE = SimpleNamespace(
    input="5 3",
    expected_output="8",
)


_ROUTE = "api.routes.submissions"


# ===========================================================================
# GET /{submission_id}/pending-review
# ===========================================================================


class TestGetPendingReview:
    def _setup(self, monkeypatch, user=STUDENT_USER):
        app = _make_app()
        _student_overrides(app, monkeypatch, user=user)
        return app, TestClient(app)

    @patch(f"{_ROUTE}.get_confidence_flags_by_transcription_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_transcription_by_submission_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_happy_path(
        self,
        mock_get_submission,
        mock_get_transcription,
        mock_get_flags,
        monkeypatch,
    ):
        _, client = self._setup(monkeypatch)
        mock_get_submission.return_value = FAKE_SUBMISSION_AWAITING
        mock_get_transcription.return_value = FAKE_TRANSCRIPTION
        mock_get_flags.return_value = [FAKE_FLAG]

        resp = client.get("/submissions/200/pending-review", headers=_auth_header())
        assert resp.status_code == 200
        body = resp.json()
        assert body["submission_id"] == 200
        assert body["transcription_id"] == 100
        assert body["transcribed_text"] == FAKE_TRANSCRIPTION.transcribed_text
        assert len(body["flags"]) == 1
        assert body["flags"][0]["id"] == 42

    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_submission_not_found(self, mock_get_submission, monkeypatch):
        _, client = self._setup(monkeypatch)
        mock_get_submission.return_value = None

        resp = client.get("/submissions/999/pending-review", headers=_auth_header())
        assert resp.status_code == 404

    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_forbidden_for_non_owner(self, mock_get_submission, monkeypatch):
        _, client = self._setup(monkeypatch, user=OTHER_STUDENT)
        mock_get_submission.return_value = FAKE_SUBMISSION_AWAITING  # owned by user 1

        resp = client.get(
            "/submissions/200/pending-review", headers=_auth_header(OTHER_STUDENT)
        )
        assert resp.status_code == 403

    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_conflict_when_not_awaiting(self, mock_get_submission, monkeypatch):
        _, client = self._setup(monkeypatch)
        mock_get_submission.return_value = FAKE_SUBMISSION_GRADED

        resp = client.get("/submissions/200/pending-review", headers=_auth_header())
        assert resp.status_code == 409

    @patch(f"{_ROUTE}.get_transcription_by_submission_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_transcription_missing(
        self, mock_get_submission, mock_get_transcription, monkeypatch
    ):
        _, client = self._setup(monkeypatch)
        mock_get_submission.return_value = FAKE_SUBMISSION_AWAITING
        mock_get_transcription.return_value = None

        resp = client.get("/submissions/200/pending-review", headers=_auth_header())
        assert resp.status_code == 404


# ===========================================================================
# POST /{submission_id}/approve-transcription
# ===========================================================================


class TestApproveTranscription:
    def _setup(self, monkeypatch, user=STUDENT_USER):
        app = _make_app()
        _student_overrides(app, monkeypatch, user=user)
        return app, TestClient(app)

    @patch(f"{_ROUTE}.start_job_process", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_testcases_by_question_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_assignment_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.update_submission_state", new_callable=AsyncMock)
    @patch(
        f"{_ROUTE}.delete_confidence_flags_by_transcription_id",
        new_callable=AsyncMock,
    )
    @patch(f"{_ROUTE}.update_transcription_text", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_transcription_by_submission_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_happy_path(
        self,
        mock_get_submission,
        mock_get_transcription,
        mock_update_text,
        mock_delete_flags,
        mock_update_state,
        mock_get_assignment,
        mock_get_testcases,
        mock_start_job,
        monkeypatch,
    ):
        _, client = self._setup(monkeypatch)
        mock_get_submission.return_value = FAKE_SUBMISSION_AWAITING
        mock_get_transcription.return_value = FAKE_TRANSCRIPTION
        mock_get_assignment.return_value = FAKE_ASSIGNMENT
        mock_get_testcases.return_value = [FAKE_TESTCASE]

        approved = "public static void main(String[] args) {"
        resp = client.post(
            "/submissions/200/approve-transcription",
            json={"approved_text": approved},
            headers=_auth_header(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["submission_id"] == 200

        # transcription text updated with the student's approved text
        mock_update_text.assert_called_once()
        text_arg = mock_update_text.call_args[0][-1]
        assert text_arg == approved

        # flags cleared for this transcription
        mock_delete_flags.assert_called_once()
        assert mock_delete_flags.call_args[0][-1] == FAKE_TRANSCRIPTION.id

        # state transitioned to processing
        mock_update_state.assert_called_once()
        assert mock_update_state.call_args[0][-1] == SubmissionState.processing

        # re-enqueue: image_url=None and java_code set (triggers skip_ocr)
        mock_start_job.assert_called_once()
        kwargs = mock_start_job.call_args.kwargs
        assert kwargs["image_url"] is None
        assert kwargs["java_code"] == approved
        assert kwargs["submission_id"] == 200

    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_submission_not_found(self, mock_get_submission, monkeypatch):
        _, client = self._setup(monkeypatch)
        mock_get_submission.return_value = None

        resp = client.post(
            "/submissions/999/approve-transcription",
            json={"approved_text": "x"},
            headers=_auth_header(),
        )
        assert resp.status_code == 404

    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_forbidden_for_non_owner(self, mock_get_submission, monkeypatch):
        _, client = self._setup(monkeypatch, user=OTHER_STUDENT)
        mock_get_submission.return_value = FAKE_SUBMISSION_AWAITING  # owned by user 1

        resp = client.post(
            "/submissions/200/approve-transcription",
            json={"approved_text": "x"},
            headers=_auth_header(OTHER_STUDENT),
        )
        assert resp.status_code == 403

    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_conflict_when_already_graded(self, mock_get_submission, monkeypatch):
        _, client = self._setup(monkeypatch)
        mock_get_submission.return_value = FAKE_SUBMISSION_GRADED

        resp = client.post(
            "/submissions/200/approve-transcription",
            json={"approved_text": "x"},
            headers=_auth_header(),
        )
        assert resp.status_code == 409

    def test_empty_approved_text_rejected(self, monkeypatch):
        # Empty text would make the re-enqueued job fall back to OCR with
        # image_url=None, which would hang. Reject at the schema level.
        _, client = self._setup(monkeypatch)

        resp = client.post(
            "/submissions/200/approve-transcription",
            json={"approved_text": ""},
            headers=_auth_header(),
        )
        assert resp.status_code == 422

    def test_instructor_cannot_approve(self, monkeypatch):
        # require_role(UserRole.student) should reject instructors
        import api.auth as auth_mod

        async def fake_lookup(session, user_id: int):
            return SimpleNamespace(
                id=user_id,
                username="prof",
                email="prof@test.com",
                role=UserRole.instructor,
                password_hash="hashed",
            )

        monkeypatch.setattr(auth_mod, "get_user_by_id", fake_lookup)

        app = _make_app()

        async def fake_get_db():
            yield None

        app.dependency_overrides[get_db] = fake_get_db

        client = TestClient(app)
        token = create_access_token({"sub": "99"})
        resp = client.post(
            "/submissions/200/approve-transcription",
            json={"approved_text": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @patch(f"{_ROUTE}.start_job_process", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_testcases_by_question_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_assignment_by_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.update_submission_state", new_callable=AsyncMock)
    @patch(
        f"{_ROUTE}.delete_confidence_flags_by_transcription_id",
        new_callable=AsyncMock,
    )
    @patch(f"{_ROUTE}.update_transcription_text", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_transcription_by_submission_id", new_callable=AsyncMock)
    @patch(f"{_ROUTE}.get_submission_by_id", new_callable=AsyncMock)
    def test_no_testcases_uses_empty_fallback(
        self,
        mock_get_submission,
        mock_get_transcription,
        mock_update_text,
        mock_delete_flags,
        mock_update_state,
        mock_get_assignment,
        mock_get_testcases,
        mock_start_job,
        monkeypatch,
    ):
        _, client = self._setup(monkeypatch)
        mock_get_submission.return_value = FAKE_SUBMISSION_AWAITING
        mock_get_transcription.return_value = FAKE_TRANSCRIPTION
        mock_get_assignment.return_value = FAKE_ASSIGNMENT
        mock_get_testcases.return_value = []

        resp = client.post(
            "/submissions/200/approve-transcription",
            json={"approved_text": "code"},
            headers=_auth_header(),
        )
        assert resp.status_code == 200
        mock_start_job.assert_called_once()
        kwargs = mock_start_job.call_args.kwargs
        assert len(kwargs["test_cases"]) == 1
        assert kwargs["test_cases"][0].input == ""
