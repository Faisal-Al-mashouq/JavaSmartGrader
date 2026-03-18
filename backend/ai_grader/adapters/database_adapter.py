from __future__ import annotations

import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class DatabaseAdapter(Protocol):
    """
    defines the essential contract for interacting with student submission
    data and AI feedback
    output: a protocol ensuring any adapter can fetch code, rubrics, and save results
    how: uses Python's Protocol to enforce a standard interface for database operations
    """

    async def get_transcription(self, submission_id: int) -> str:
        """Return transcribed student code."""

    async def get_sandbox_results(self, submission_id: int) -> str:
        """Return compile/runtime logs."""

    async def get_rubric(self, submission_id: int) -> Any:
        """Return rubric payload from DB."""

    async def save_feedback(
        self,
        submission_id: int,
        parsed_feedback: dict[str, Any],
    ) -> None:
        """Persist suggested grade + detailed AI feedback."""

    async def persist_failure_feedback(
        self,
        submission_id: int,
        reason: str,
        raw_output: str,
    ) -> None:
        """Persist a failure feedback record if possible."""

    async def update_status(self, submission_id: int, new_status: str) -> bool:
        """Update submission state if compatible with available enum values."""

    async def mark_failure_status(
        self,
        submission_id: int,
        candidates: tuple[str, ...],
    ) -> bool:
        """Set first available failure status from candidates."""


class SQLAlchemyDatabaseAdapter:
    """
    implements the adapter using SQLAlchemy to communicate with a relational database
    output: performs real-time CRUD operations for grading data and submission statuses
    how: dynamically loads backend modules and uses asynchronous sessions to
    execute queries
    """

    def __init__(self, backend_path: Path):
        self._load_backend_modules(backend_path)

    def _load_backend_modules(self, backend_path: Path) -> None:
        normalized_path = str(backend_path.resolve())
        if normalized_path not in sys.path:
            sys.path.insert(0, normalized_path)

        session_module = importlib.import_module("db.session")
        models_module = importlib.import_module("db.models")
        sqlalchemy_module = importlib.import_module("sqlalchemy")
        sqlalchemy_orm_module = importlib.import_module("sqlalchemy.orm")

        self._async_session_factory = session_module.async_session
        self._Submission = models_module.Submission
        self._SubmissionState = models_module.SubmissionState
        self._AIFeedback = models_module.AIFeedback
        self._select = sqlalchemy_module.select
        self._update = sqlalchemy_module.update
        self._selectinload = sqlalchemy_orm_module.selectinload

    @staticmethod
    def _normalize_status(value: str) -> str:
        return value.strip().lower().replace(" ", "_")

    async def _get_submission(self, submission_id: int):
        async with self._async_session_factory() as session:
            result = await session.execute(
                self._select(self._Submission)
                .options(
                    self._selectinload(self._Submission.transcription),
                    self._selectinload(self._Submission.compile_results),
                    self._selectinload(self._Submission.assignment),
                    self._selectinload(self._Submission.ai_feedback),
                )
                .where(self._Submission.id == submission_id)
            )
            submission = result.scalar_one_or_none()
            return submission

    async def get_transcription(self, submission_id: int) -> str:
        submission = await self._get_submission(submission_id)
        if submission is None:
            raise LookupError(f"Submission {submission_id} not found")
        transcription = getattr(submission, "transcription", None)
        if transcription is None or transcription.transcribed_text is None:
            return ""
        return transcription.transcribed_text

    async def get_sandbox_results(self, submission_id: int) -> str:
        submission = await self._get_submission(submission_id)
        if submission is None:
            raise LookupError(f"Submission {submission_id} not found")
        compile_result = getattr(submission, "compile_results", None)
        if compile_result is None:
            return ""

        return "\n".join(
            [
                f"compiled_ok: {compile_result.compiled_ok}",
                "compile_errors:",
                compile_result.compile_errors or "",
                "runtime_errors:",
                compile_result.runtime_errors or "",
                "runtime_output:",
                (
                    getattr(compile_result, "runtime_outputs", None)
                    or getattr(compile_result, "runtime_output", None)
                    or ""
                ),
            ]
        )

    async def get_rubric(self, submission_id: int) -> Any:
        submission = await self._get_submission(submission_id)
        if submission is None:
            raise LookupError(f"Submission {submission_id} not found")
        assignment = getattr(submission, "assignment", None)
        if assignment is None:
            return {"rubric_missing": True}
        return assignment.rubric_json

    async def save_feedback(
        self,
        submission_id: int,
        parsed_feedback: dict[str, Any],
    ) -> None:
        feedback_text = json.dumps(parsed_feedback, ensure_ascii=True, indent=2)
        total_score = parsed_feedback.get("total_score")
        suggested_grade = float(total_score) if total_score is not None else None
        feedback_summary = None
        feedback = parsed_feedback.get("feedback")
        if isinstance(feedback, dict):
            summary = feedback.get("summary")
            if isinstance(summary, str):
                feedback_summary = summary

        async with self._async_session_factory() as session:
            existing_result = await session.execute(
                self._select(self._AIFeedback).where(
                    self._AIFeedback.submission_id == submission_id
                )
            )
            existing_feedback = existing_result.scalar_one_or_none()
            if existing_feedback is None:
                session.add(
                    self._AIFeedback(
                        submission_id=submission_id,
                        suggested_grade=suggested_grade,
                        instructor_guidance=feedback_text,
                        student_feedback=feedback_summary,
                    )
                )
            else:
                existing_feedback.suggested_grade = suggested_grade
                existing_feedback.instructor_guidance = feedback_text
                existing_feedback.student_feedback = feedback_summary

            await session.commit()

    async def persist_failure_feedback(
        self,
        submission_id: int,
        reason: str,
        raw_output: str,
    ) -> None:
        failure_payload = {
            "submission_id": submission_id,
            "status": "ai_grading_failed",
            "reason": reason,
            "raw_model_output": raw_output,
        }
        failure_text = json.dumps(failure_payload, ensure_ascii=True, indent=2)

        async with self._async_session_factory() as session:
            existing_result = await session.execute(
                self._select(self._AIFeedback).where(
                    self._AIFeedback.submission_id == submission_id
                )
            )
            existing_feedback = existing_result.scalar_one_or_none()
            if existing_feedback is None:
                session.add(
                    self._AIFeedback(
                        submission_id=submission_id,
                        suggested_grade=None,
                        instructor_guidance=failure_text,
                        student_feedback=None,
                    )
                )
            else:
                existing_feedback.suggested_grade = None
                existing_feedback.instructor_guidance = failure_text
                existing_feedback.student_feedback = None

            await session.commit()

    def _coerce_status(self, value: str):
        normalized_target = self._normalize_status(value)
        for state in self._SubmissionState:
            if self._normalize_status(state.value) == normalized_target:
                return state
        return None

    async def update_status(self, submission_id: int, new_status: str) -> bool:
        coerced_state = self._coerce_status(new_status)
        if coerced_state is None:
            logger.warning(
                "Status '%s' is not available in submission_state enum. "
                "Leaving submission %s unchanged.",
                new_status,
                submission_id,
            )
            return False

        async with self._async_session_factory() as session:
            result = await session.execute(
                self._update(self._Submission)
                .where(self._Submission.id == submission_id)
                .values(state=coerced_state)
            )
            await session.commit()
            return bool(result.rowcount)

    async def mark_failure_status(
        self,
        submission_id: int,
        candidates: tuple[str, ...],
    ) -> bool:
        for candidate in candidates:
            if await self.update_status(submission_id, candidate):
                return True
        return False


class PlaceholderDatabaseAdapter:
    """
    acts as a "safety net" if the primary database backend fails to load or import
    output: raises a descriptive RuntimeError whenever any database method is called
    how: stores the original import error and triggers it via a private helper method
    """

    def __init__(self, root_error: Exception):
        self._root_error = root_error

    def _raise_unconfigured(self) -> None:
        raise RuntimeError(
            "Database adapter could not import backend modules. "
            "Map this adapter to your project DB implementation. "
            f"Import error: {self._root_error}"
        )

    async def get_transcription(self, submission_id: int) -> str:
        self._raise_unconfigured()

    async def get_sandbox_results(self, submission_id: int) -> str:
        self._raise_unconfigured()

    async def get_rubric(self, submission_id: int) -> Any:
        self._raise_unconfigured()

    async def save_feedback(
        self,
        submission_id: int,
        parsed_feedback: dict[str, Any],
    ) -> None:
        self._raise_unconfigured()

    async def persist_failure_feedback(
        self,
        submission_id: int,
        reason: str,
        raw_output: str,
    ) -> None:
        self._raise_unconfigured()

    async def update_status(self, submission_id: int, new_status: str) -> bool:
        self._raise_unconfigured()

    async def mark_failure_status(
        self,
        submission_id: int,
        candidates: tuple[str, ...],
    ) -> bool:
        self._raise_unconfigured()


def create_database_adapter(backend_path: Path) -> DatabaseAdapter:
    """
    a factory function that attempts to initialize the real database connection
    output: Returns either a fully functional SQLAlchemyDatabaseAdapter or
    the placeholder
    how: Uses a try-except block to catch configuration errors and log them as warnings
    """
    try:
        return SQLAlchemyDatabaseAdapter(backend_path=backend_path)
    except Exception as exc:
        logger.warning(
            "Falling back to placeholder DB adapter because backend imports failed: %s",
            exc,
        )
        return PlaceholderDatabaseAdapter(exc)
