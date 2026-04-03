"""End-to-end HTTP tests: register → course → assignment → question → enroll → submit.

Requires a running API (see ``E2E_API_BASE``) and S3/MinIO access for ``get_file`` (same as
``api.test_job``). Run::

    uv run pytest tests/test_submission.py -v -m e2e

Skip automatically when the API is unreachable (no server on the configured base URL).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from io import BytesIO

import httpx
import pytest
from api.s3 import get_file
from db.models import SubmissionState

RUBRIC = {
    "criteria": {
        "Correctness": {"weight": 100, "description": "Correct"},
        "Code Quality": {"weight": 100, "description": "Code Quality"},
    }
}
QUESTION_TEXT = """Make a simple vending machine program that takes in a number
of snacks and checks if there's enough stock. If there's not enough stock, print
an error message. The snack count is 10."""
IMAGE_KEY = "submissions/1/page.png"


def _base_url() -> str:
    return os.environ.get("E2E_API_BASE", "http://localhost:8000").rstrip("/")


@pytest.fixture(scope="module")
def e2e_api_base() -> str:
    return _base_url()


@pytest.fixture(scope="module")
def e2e_run_id() -> str:
    return uuid.uuid4().hex[:12]


@pytest.fixture(scope="module")
def require_live_api(e2e_api_base: str) -> None:
    try:
        r = httpx.get(f"{e2e_api_base}/openapi.json", timeout=5.0)
        r.raise_for_status()
    except (httpx.HTTPError, OSError) as e:
        pytest.skip(f"E2E API not available at {e2e_api_base}: {e}")


@pytest.fixture
def student_identity(e2e_run_id: str) -> dict[str, str]:
    s = e2e_run_id
    return {
        "username": f"e2e_student_{s}",
        "password": "testpass123",
        "email": f"e2e_student_{s}@test.local",
    }


@pytest.fixture
def instructor_identity(e2e_run_id: str) -> dict[str, str]:
    s = e2e_run_id
    return {
        "username": f"e2e_instructor_{s}",
        "password": "testpass123",
        "email": f"e2e_instructor_{s}@test.local",
    }


def _register(
    client: httpx.Client,
    *,
    username: str,
    password: str,
    email: str,
    role: str,
) -> None:
    r = client.post(
        "/users/register",
        json={"username": username, "password": password, "email": email, "role": role},
    )
    r.raise_for_status()


def _login(client: httpx.Client, *, username: str, password: str) -> str:
    r = client.post(
        "/users/login",
        data={"username": username, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _create_course(
    client: httpx.Client,
    *,
    instructor_headers: dict[str, str],
    name: str,
) -> int:
    r = client.post(
        "/courses/",
        params={"name": name, "description": "E2E pytest"},
        headers=instructor_headers,
    )
    r.raise_for_status()
    return r.json()["id"]


def _create_assignment(
    client: httpx.Client,
    *,
    course_id: int,
    title: str,
    instructor_headers: dict[str, str],
) -> int:
    r = client.post(
        "/assignments/",
        params={
            "course_id": course_id,
            "title": title,
            "description": "E2E assignment",
        },
        json=RUBRIC,
        headers=instructor_headers,
    )
    r.raise_for_status()
    return r.json()["id"]


def _create_question(
    client: httpx.Client,
    *,
    assignment_id: int,
    instructor_headers: dict[str, str],
) -> int:
    r = client.post(
        f"/assignments/{assignment_id}/questions/",
        params={"question_text": QUESTION_TEXT},
        headers=instructor_headers,
    )
    r.raise_for_status()
    return r.json()["id"]


def _enroll_student(
    client: httpx.Client,
    *,
    course_id: int,
    student_id: int,
    instructor_headers: dict[str, str],
) -> None:
    r = client.post(
        f"/courses/{course_id}/enroll/{student_id}",
        headers=instructor_headers,
    )
    if r.status_code not in (200, 201, 409):
        r.raise_for_status()


@pytest.fixture
def e2e_http_client(e2e_api_base: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=e2e_api_base, timeout=60.0) as client:
        yield client


@pytest.mark.e2e
def test_submission_flow_creates_submission_with_expected_shape(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
    student_identity: dict[str, str],
    instructor_identity: dict[str, str],
) -> None:
    client = e2e_http_client

    _register(
        client,
        **student_identity,
        role="student",
    )
    _register(
        client,
        **instructor_identity,
        role="instructor",
    )

    student_token = _login(
        client,
        username=student_identity["username"],
        password=student_identity["password"],
    )
    instructor_token = _login(
        client,
        username=instructor_identity["username"],
        password=instructor_identity["password"],
    )
    inst_headers = {"Authorization": f"Bearer {instructor_token}"}

    course_id = _create_course(
        client,
        instructor_headers=inst_headers,
        name=f"E2E Course {e2e_run_id}",
    )
    assignment_id = _create_assignment(
        client,
        course_id=course_id,
        title=f"Assignment {e2e_run_id}",
        instructor_headers=inst_headers,
    )
    question_id = _create_question(
        client,
        assignment_id=assignment_id,
        instructor_headers=inst_headers,
    )

    me = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    me.raise_for_status()
    student_id = me.json()["id"]

    _enroll_student(
        client,
        course_id=course_id,
        student_id=student_id,
        instructor_headers=inst_headers,
    )

    file_bytes = get_file(IMAGE_KEY)
    resp = client.post(
        "/submissions/",
        data={
            "question_id": str(question_id),
            "assignment_id": str(assignment_id),
        },
        headers={"Authorization": f"Bearer {student_token}"},
        files={"file": ("page.png", BytesIO(file_bytes), "image/png")},
    )
    resp.raise_for_status()
    body = resp.json()

    assert isinstance(body["id"], int)
    assert body["question_id"] == question_id
    assert body["assignment_id"] == assignment_id
    assert body["student_id"] == student_id
    assert body["state"] in {s.value for s in SubmissionState}
