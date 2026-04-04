"""New E2E tests: course CRUD, assignment management, question + testcases,
enrollment lifecycle, error cases, and student submissions retrieval.

Requires a running API (see ``E2E_API_BASE``).  Run::

    uv run pytest tests/test_e2e_new.py -v -m e2e

Skips automatically when the API is unreachable.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import httpx
import pytest

RUBRIC = {"criteria": {"Correctness": {"weight": 100, "description": "Correct"}}}


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


@pytest.fixture(scope="module")
def e2e_http_client(e2e_api_base: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=e2e_api_base, timeout=60.0) as client:
        yield client


# --- Helpers ---


def _register(
    client: httpx.Client, *, username: str, password: str, email: str, role: str
):
    r = client.post(
        "/users/register",
        json={"username": username, "password": password, "email": email, "role": role},
    )
    r.raise_for_status()
    return r.json()


def _login(client: httpx.Client, *, username: str, password: str) -> str:
    r = client.post("/users/login", data={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Test: Course CRUD lifecycle ---


@pytest.mark.e2e
def test_course_crud_lifecycle(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    """Create → read → update → delete a course."""
    client = e2e_http_client
    tag = e2e_run_id

    # Register instructor
    _register(
        client,
        username=f"e2e_crud_inst_{tag}",
        password="testpass123",
        email=f"e2e_crud_inst_{tag}@test.local",
        role="instructor",
    )
    token = _login(client, username=f"e2e_crud_inst_{tag}", password="testpass123")
    headers = _auth(token)

    # Create
    resp = client.post(
        "/courses/",
        params={"name": f"CrudCourse {tag}", "description": "test desc"},
        headers=headers,
    )
    assert resp.status_code == 200
    course = resp.json()
    course_id = course["id"]
    assert course["name"] == f"CrudCourse {tag}"
    assert course["description"] == "test desc"

    # Read
    resp = client.get(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == course_id

    # Update
    resp = client.put(
        f"/courses/{course_id}",
        params={"name": f"Updated {tag}"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == f"Updated {tag}"

    # Delete
    resp = client.delete(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 200

    # Confirm deleted
    resp = client.get(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 404


# --- Test: Assignment CRUD ---


@pytest.mark.e2e
def test_assignment_crud_lifecycle(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    """Create → read → update → delete an assignment."""
    client = e2e_http_client
    tag = e2e_run_id

    _register(
        client,
        username=f"e2e_assign_inst_{tag}",
        password="testpass123",
        email=f"e2e_assign_inst_{tag}@test.local",
        role="instructor",
    )
    token = _login(client, username=f"e2e_assign_inst_{tag}", password="testpass123")
    headers = _auth(token)

    # Create course first
    resp = client.post(
        "/courses/", params={"name": f"AssignCourse {tag}"}, headers=headers
    )
    resp.raise_for_status()
    course_id = resp.json()["id"]

    # Create assignment
    resp = client.post(
        "/assignments/",
        params={
            "course_id": course_id,
            "title": f"HW {tag}",
            "description": "Test assignment",
        },
        json=RUBRIC,
        headers=headers,
    )
    assert resp.status_code == 200
    assignment = resp.json()
    assignment_id = assignment["id"]
    assert assignment["title"] == f"HW {tag}"
    assert assignment["rubric_json"] is not None

    # Read
    resp = client.get(f"/assignments/{assignment_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["course_id"] == course_id

    # List by course
    resp = client.get(f"/assignments/course/{course_id}", headers=headers)
    assert resp.status_code == 200
    assert any(a["id"] == assignment_id for a in resp.json())

    # Update
    resp = client.put(
        f"/assignments/{assignment_id}",
        params={"title": f"Updated HW {tag}"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == f"Updated HW {tag}"

    # Delete
    resp = client.delete(f"/assignments/{assignment_id}", headers=headers)
    assert resp.status_code == 200


# --- Test: Question + Testcase CRUD ---


@pytest.mark.e2e
def test_question_and_testcase_crud(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    """Create question → add testcases → list → delete."""
    client = e2e_http_client
    tag = e2e_run_id

    _register(
        client,
        username=f"e2e_q_inst_{tag}",
        password="testpass123",
        email=f"e2e_q_inst_{tag}@test.local",
        role="instructor",
    )
    token = _login(client, username=f"e2e_q_inst_{tag}", password="testpass123")
    headers = _auth(token)

    # Setup: course + assignment
    resp = client.post("/courses/", params={"name": f"QCourse {tag}"}, headers=headers)
    resp.raise_for_status()
    course_id = resp.json()["id"]

    resp = client.post(
        "/assignments/",
        params={"course_id": course_id, "title": f"QAssign {tag}"},
        json=RUBRIC,
        headers=headers,
    )
    resp.raise_for_status()
    assignment_id = resp.json()["id"]

    # Create question
    resp = client.post(
        f"/assignments/{assignment_id}/questions/",
        params={"question_text": "Write a program that adds two numbers"},
        headers=headers,
    )
    assert resp.status_code == 200
    question = resp.json()
    question_id = question["id"]
    assert question["question_text"] == "Write a program that adds two numbers"

    # Add testcase
    resp = client.post(
        f"/assignments/{assignment_id}/questions/{question_id}/testcases",
        params={"input_data": "3 5", "expected_output": "8"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Add second testcase
    resp = client.post(
        f"/assignments/{assignment_id}/questions/{question_id}/testcases",
        params={"input_data": "10 20", "expected_output": "30"},
        headers=headers,
    )
    assert resp.status_code == 200

    # List testcases
    resp = client.get(
        f"/assignments/{assignment_id}/questions/{question_id}/testcases",
        headers=headers,
    )
    assert resp.status_code == 200
    testcases = resp.json()
    assert len(testcases) >= 2

    # Delete testcases first (no cascade on question delete)
    for tc in testcases:
        resp = client.delete(
            f"/assignments/{assignment_id}/questions/{question_id}/testcases/{tc['id']}",
            headers=headers,
        )
        assert resp.status_code == 200

    # Delete question
    resp = client.delete(
        f"/assignments/{assignment_id}/questions/{question_id}",
        headers=headers,
    )
    assert resp.status_code == 200


# --- Test: Student enrollment lifecycle ---


@pytest.mark.e2e
def test_enrollment_lifecycle(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    """Enroll → verify access → unenroll → verify denied."""
    client = e2e_http_client
    tag = e2e_run_id

    # Register instructor + student
    _register(
        client,
        username=f"e2e_enr_inst_{tag}",
        password="testpass123",
        email=f"e2e_enr_inst_{tag}@test.local",
        role="instructor",
    )
    _register(
        client,
        username=f"e2e_enr_stu_{tag}",
        password="testpass123",
        email=f"e2e_enr_stu_{tag}@test.local",
        role="student",
    )
    inst_token = _login(client, username=f"e2e_enr_inst_{tag}", password="testpass123")
    stu_token = _login(client, username=f"e2e_enr_stu_{tag}", password="testpass123")
    inst_headers = _auth(inst_token)
    stu_headers = _auth(stu_token)

    # Get student ID
    me = client.get("/users/me", headers=stu_headers)
    me.raise_for_status()
    student_id = me.json()["id"]

    # Create course
    resp = client.post(
        "/courses/", params={"name": f"EnrCourse {tag}"}, headers=inst_headers
    )
    resp.raise_for_status()
    course_id = resp.json()["id"]

    # Student can't see course before enrollment
    resp = client.get(f"/courses/{course_id}", headers=stu_headers)
    assert resp.status_code == 403

    # Enroll
    resp = client.post(
        f"/courses/{course_id}/enroll/{student_id}", headers=inst_headers
    )
    assert resp.status_code == 200

    # Now student can see course
    resp = client.get(f"/courses/{course_id}", headers=stu_headers)
    assert resp.status_code == 200

    # Double enroll should fail with 409
    resp = client.post(
        f"/courses/{course_id}/enroll/{student_id}", headers=inst_headers
    )
    assert resp.status_code == 409

    # Unenroll
    resp = client.delete(
        f"/courses/{course_id}/enroll/{student_id}", headers=inst_headers
    )
    assert resp.status_code == 200

    # Student can't see course after unenrollment
    resp = client.get(f"/courses/{course_id}", headers=stu_headers)
    assert resp.status_code == 403


# --- Test: Auth error cases ---


@pytest.mark.e2e
def test_duplicate_registration_returns_409(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    client = e2e_http_client
    tag = e2e_run_id
    identity = {
        "username": f"e2e_dup_{tag}",
        "password": "testpass123",
        "email": f"e2e_dup_{tag}@test.local",
        "role": "student",
    }
    resp = client.post("/users/register", json=identity)
    assert resp.status_code == 200

    resp = client.post("/users/register", json=identity)
    assert resp.status_code == 409


@pytest.mark.e2e
def test_login_with_wrong_password_returns_401(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    client = e2e_http_client
    tag = e2e_run_id
    _register(
        client,
        username=f"e2e_badlogin_{tag}",
        password="correctpass",
        email=f"e2e_badlogin_{tag}@test.local",
        role="student",
    )
    resp = client.post(
        "/users/login",
        data={"username": f"e2e_badlogin_{tag}", "password": "wrongpass"},
    )
    assert resp.status_code == 401


@pytest.mark.e2e
def test_login_nonexistent_user_returns_401(
    require_live_api: None,
    e2e_http_client: httpx.Client,
) -> None:
    client = e2e_http_client
    resp = client.post(
        "/users/login",
        data={"username": "nonexistent_user_xyz", "password": "pass"},
    )
    assert resp.status_code == 401


@pytest.mark.e2e
def test_student_cannot_create_course(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    """Students should be blocked from instructor-only endpoints."""
    client = e2e_http_client
    tag = e2e_run_id
    _register(
        client,
        username=f"e2e_stublock_{tag}",
        password="testpass123",
        email=f"e2e_stublock_{tag}@test.local",
        role="student",
    )
    token = _login(client, username=f"e2e_stublock_{tag}", password="testpass123")
    headers = _auth(token)

    resp = client.post("/courses/", params={"name": "Should Fail"}, headers=headers)
    assert resp.status_code == 403


@pytest.mark.e2e
def test_instructor_can_list_students(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    client = e2e_http_client
    tag = e2e_run_id
    _register(
        client,
        username=f"e2e_liststud_inst_{tag}",
        password="testpass123",
        email=f"e2e_liststud_inst_{tag}@test.local",
        role="instructor",
    )
    token = _login(client, username=f"e2e_liststud_inst_{tag}", password="testpass123")
    resp = client.get("/users/students", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.e2e
def test_get_my_courses_returns_list(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    client = e2e_http_client
    tag = e2e_run_id
    _register(
        client,
        username=f"e2e_mycourses_{tag}",
        password="testpass123",
        email=f"e2e_mycourses_{tag}@test.local",
        role="instructor",
    )
    token = _login(client, username=f"e2e_mycourses_{tag}", password="testpass123")
    resp = client.get("/courses/me", headers=_auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.e2e
def test_get_user_profile(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    client = e2e_http_client
    tag = e2e_run_id
    _register(
        client,
        username=f"e2e_profile_{tag}",
        password="testpass123",
        email=f"e2e_profile_{tag}@test.local",
        role="student",
    )
    token = _login(client, username=f"e2e_profile_{tag}", password="testpass123")
    resp = client.get("/users/me", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == f"e2e_profile_{tag}"
    assert body["email"] == f"e2e_profile_{tag}@test.local"
    assert body["role"] == "student"


@pytest.mark.e2e
def test_course_not_found_returns_404(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    client = e2e_http_client
    tag = e2e_run_id
    _register(
        client,
        username=f"e2e_404_{tag}",
        password="testpass123",
        email=f"e2e_404_{tag}@test.local",
        role="instructor",
    )
    token = _login(client, username=f"e2e_404_{tag}", password="testpass123")
    resp = client.get("/courses/999999", headers=_auth(token))
    assert resp.status_code == 404


@pytest.mark.e2e
def test_update_course_no_fields_returns_400(
    require_live_api: None,
    e2e_http_client: httpx.Client,
    e2e_run_id: str,
) -> None:
    client = e2e_http_client
    tag = e2e_run_id
    _register(
        client,
        username=f"e2e_nofield_{tag}",
        password="testpass123",
        email=f"e2e_nofield_{tag}@test.local",
        role="instructor",
    )
    token = _login(client, username=f"e2e_nofield_{tag}", password="testpass123")
    headers = _auth(token)

    resp = client.post(
        "/courses/", params={"name": f"NoFieldCourse {tag}"}, headers=headers
    )
    resp.raise_for_status()
    course_id = resp.json()["id"]

    # Update with no fields
    resp = client.put(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 400
