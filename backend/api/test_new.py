"""New unit tests for API auth edge cases and schema validation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from db.models import UserRole
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from schemas import (
    AssignmentBase,
    CourseBase,
    LoginRequest,
    QuestionBase,
    RegisterRequest,
    TestcaseBase,
    UserBase,
)

from api.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_current_user,
    require_role,
)
from api.dependencies import get_db

# --- Token edge cases ---


def test_create_access_token_includes_custom_claims() -> None:
    token = create_access_token(
        {"sub": "42", "role": UserRole.instructor.value, "custom": "val"}
    )
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "42"
    assert decoded["role"] == UserRole.instructor.value
    assert decoded["custom"] == "val"
    assert "exp" in decoded


def test_create_access_token_empty_data() -> None:
    token = create_access_token({})
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in decoded
    assert "sub" not in decoded


def test_token_with_missing_sub_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        raise AssertionError("should not be called")

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    app = FastAPI()

    @app.get("/test")
    async def test_route(_=Depends(get_current_user)):
        return {"ok": True}

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db

    # Token without 'sub' claim
    token = jwt.encode({"role": "student"}, SECRET_KEY, algorithm=ALGORITHM)
    client = TestClient(app)
    resp = client.get("/test", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_no_auth_header_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        return None

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    app = FastAPI()

    @app.get("/test")
    async def test_route(_=Depends(get_current_user)):
        return {"ok": True}

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 401


# --- require_role tests ---


def test_require_role_allows_correct_role(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        return SimpleNamespace(
            id=user_id,
            username="prof",
            email="prof@test.com",
            role=UserRole.instructor,
            password_hash="hashed",
        )

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    app = FastAPI()

    @app.get("/instructor-only")
    async def instructor_route(user=Depends(require_role(UserRole.instructor))):
        return {"id": user.id, "role": user.role.value}

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db

    token = create_access_token({"sub": "5"})
    client = TestClient(app)
    resp = client.get("/instructor-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "instructor"


def test_require_role_instructor_blocks_student(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        return SimpleNamespace(
            id=user_id,
            username="student1",
            email="s@test.com",
            role=UserRole.student,
            password_hash="hashed",
        )

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    app = FastAPI()

    @app.get("/instructor-only")
    async def instructor_route(_=Depends(require_role(UserRole.instructor))):
        return {"ok": True}

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db

    token = create_access_token({"sub": "10"})
    client = TestClient(app)
    resp = client.get("/instructor-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Forbidden"


# --- Pydantic schema validation tests ---


def test_user_base_schema():
    user = UserBase(
        id=1, username="alice", email="alice@test.com", role=UserRole.student
    )
    assert user.id == 1
    assert user.role == UserRole.student


def test_register_request_schema():
    req = RegisterRequest(
        username="bob",
        password="pass123",
        email="bob@test.com",
        role=UserRole.instructor,
    )
    assert req.username == "bob"
    assert req.role == UserRole.instructor


def test_login_request_schema():
    req = LoginRequest(username="alice", password="secret")
    assert req.username == "alice"


def test_course_base_schema():
    course = CourseBase(id=1, name="CS101", description="Intro to CS", instructor_id=5)
    assert course.name == "CS101"
    assert course.instructor_id == 5


def test_course_base_optional_description():
    course = CourseBase(id=2, name="CS202", instructor_id=3)
    assert course.description is None


def test_assignment_base_schema():
    assignment = AssignmentBase(
        id=1,
        course_id=1,
        title="HW1",
        description="First assignment",
        rubric_json={"criteria": {"Correctness": {"weight": 100}}},
    )
    assert assignment.title == "HW1"
    assert assignment.rubric_json is not None


def test_assignment_base_optional_fields():
    assignment = AssignmentBase(id=2, course_id=1, title="HW2")
    assert assignment.description is None
    assert assignment.due_date is None
    assert assignment.rubric_json is None


def test_question_base_schema():
    q = QuestionBase(id=1, assignment_id=1, question_text="Write hello world")
    assert q.question_text == "Write hello world"


def test_testcase_base_schema():
    tc = TestcaseBase(
        id=1,
        question_id=1,
        assignment_id=1,
        input="5 3",
        expected_output="8",
    )
    assert tc.input == "5 3"
    assert tc.expected_output == "8"


def test_register_request_roundtrip():
    req = RegisterRequest(
        username="test", password="pass", email="t@t.com", role=UserRole.student
    )
    raw = req.model_dump_json()
    restored = RegisterRequest.model_validate_json(raw)
    assert restored.username == req.username
    assert restored.role == req.role


def test_user_base_from_attributes():
    obj = SimpleNamespace(
        id=10, username="test", email="test@test.com", role=UserRole.instructor
    )
    user = UserBase.model_validate(obj, from_attributes=True)
    assert user.id == 10
    assert user.role == UserRole.instructor
