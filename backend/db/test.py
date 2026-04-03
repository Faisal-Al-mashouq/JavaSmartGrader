from __future__ import annotations

import pytest
from schemas import UserBase

from db.models import (
    Assignment,
    Base,
    Course,
    GenerateReport,
    Grade,
    Question,
    Submission,
    SubmissionState,
    User,
    UserRole,
)


@pytest.mark.parametrize(
    "role, value",
    [
        (UserRole.student, "student"),
        (UserRole.instructor, "instructor"),
    ],
)
def test_user_role_enum_values(role: UserRole, value: str) -> None:
    assert role.value == value


@pytest.mark.parametrize(
    "state, value",
    [
        (SubmissionState.submitted, "submitted"),
        (SubmissionState.processing, "processing"),
        (SubmissionState.graded, "graded"),
        (SubmissionState.failed, "failed"),
    ],
)
def test_submission_state_enum_values(state: SubmissionState, value: str) -> None:
    assert state.value == value


@pytest.mark.parametrize(
    "model, expected_name",
    [
        (User, "users"),
        (Course, "courses"),
        (Assignment, "assignments"),
        (Question, "questions"),
        (Submission, "submissions"),
        (Grade, "grades"),
        (GenerateReport, "generate_reports"),
    ],
)
def test_model_tablenames(model, expected_name: str) -> None:
    assert model.__tablename__ == expected_name


def test_association_table_registered() -> None:
    assert "course_students" in Base.metadata.tables


def test_core_tables_in_metadata() -> None:
    names = set(Base.metadata.tables)
    assert {
        "users",
        "courses",
        "assignments",
        "questions",
        "submissions",
        "testcases",
        "ai_feedback",
        "compile_results",
        "transcriptions",
        "confidence_flags",
        "grades",
        "generate_reports",
        "course_students",
    }.issubset(names)


def test_user_repr() -> None:
    u = User(
        id=1,
        username="alice",
        email="a@example.com",
        role=UserRole.student,
        password_hash="hash",
    )
    r = repr(u)
    assert "alice" in r
    assert "student" in r


def test_user_base_from_attributes() -> None:
    u = User(
        id=2,
        username="bob",
        email="bob@example.com",
        role=UserRole.instructor,
        password_hash="hash",
    )
    dto = UserBase.model_validate(u)
    assert dto.id == 2
    assert dto.username == "bob"
    assert dto.role == UserRole.instructor
