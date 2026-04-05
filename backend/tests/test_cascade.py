"""E2E tests: DB schema cascade and FK constraint corner cases.

Probes what happens when deleting entities that have dependent records.
Verifies that DB-level CASCADE and RESTRICT constraints work correctly.

Tables with DB-level CASCADE (deleting parent removes children):
    - ai_feedback, compile_results, transcriptions, grades -> submissions.id
    - confidence_flags -> transcriptions.id
    - questions -> assignments.id
    - testcases -> questions(id, assignment_id)
    - submissions -> questions(id, assignment_id)
    - assignments -> courses.id
    - course_students -> courses.id / users.id
    - generate_reports -> assignments.id

Tables with DB-level RESTRICT (deleting parent blocked while children exist):
    - courses -> users.id (instructor_id)
    - submissions -> users.id (student_id)
    - grades -> users.id (instructor_id)

Run::

    uv run pytest tests/test_cascade.py -v -m e2e
"""

from __future__ import annotations

import io
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


@pytest.fixture()
def client(e2e_api_base: str) -> Iterator[httpx.Client]:
    """Function-scoped client -- each test gets a fresh TCP connection pool."""
    with httpx.Client(base_url=e2e_api_base, timeout=60.0) as c:
        yield c


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


def _setup_instructor(client: httpx.Client, tag: str, suffix: str = ""):
    """Register and login an instructor, return (token, headers)."""
    name = f"e2e_casc_{suffix}_{tag}"
    _register(
        client,
        username=name,
        password="testpass123",
        email=f"{name}@test.local",
        role="instructor",
    )
    token = _login(client, username=name, password="testpass123")
    return token, _auth(token)


def _setup_student(client: httpx.Client, tag: str, suffix: str = ""):
    """Register and login a student, return (student_id, token, headers)."""
    name = f"e2e_casc_stu_{suffix}_{tag}"
    _register(
        client,
        username=name,
        password="testpass123",
        email=f"{name}@test.local",
        role="student",
    )
    token = _login(client, username=name, password="testpass123")
    headers = _auth(token)
    me = client.get("/users/me", headers=headers)
    me.raise_for_status()
    return me.json()["id"], token, headers


def _create_course(
    client: httpx.Client, headers: dict, tag: str, suffix: str = ""
) -> int:
    resp = client.post(
        "/courses/", params={"name": f"CascCourse_{suffix}_{tag}"}, headers=headers
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _create_assignment(
    client: httpx.Client, headers: dict, course_id: int, tag: str, suffix: str = ""
) -> int:
    resp = client.post(
        "/assignments/",
        params={"course_id": course_id, "title": f"CascHW_{suffix}_{tag}"},
        json=RUBRIC,
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _create_question(client: httpx.Client, headers: dict, assignment_id: int) -> int:
    resp = client.post(
        f"/assignments/{assignment_id}/questions/",
        params={"question_text": "Cascade test question"},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _create_testcase(
    client: httpx.Client, headers: dict, assignment_id: int, question_id: int
):
    resp = client.post(
        f"/assignments/{assignment_id}/questions/{question_id}/testcases",
        params={"input_data": "1 2", "expected_output": "3"},
        headers=headers,
    )
    resp.raise_for_status()
    return resp.json()


def _get_testcases(
    client: httpx.Client, headers: dict, assignment_id: int, question_id: int
) -> list:
    resp = client.get(
        f"/assignments/{assignment_id}/questions/{question_id}/testcases",
        headers=headers,
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


# ======================================================================
# 1. CASCADE: Delete question with testcases (DB CASCADE on testcases->questions)
# ======================================================================


@pytest.mark.e2e
def test_delete_question_with_testcases_cascades(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a question should cascade-delete its testcases."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "q_tc")

    course_id = _create_course(client, headers, tag, "q_tc")
    assignment_id = _create_assignment(client, headers, course_id, tag, "q_tc")
    question_id = _create_question(client, headers, assignment_id)
    _create_testcase(client, headers, assignment_id, question_id)
    _create_testcase(client, headers, assignment_id, question_id)

    resp = client.delete(
        f"/assignments/{assignment_id}/questions/{question_id}",
        headers=headers,
    )
    assert (
        resp.status_code == 200
    ), f"Expected cascade delete to succeed, got {resp.status_code}"

    # Question should be gone
    resp = client.get(
        f"/assignments/{assignment_id}/questions/{question_id}",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.e2e
def test_delete_question_after_removing_testcases_succeeds(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a question succeeds once its testcases are removed first (manual cleanup still works)."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "q_clean")

    course_id = _create_course(client, headers, tag, "q_clean")
    assignment_id = _create_assignment(client, headers, course_id, tag, "q_clean")
    question_id = _create_question(client, headers, assignment_id)
    _create_testcase(client, headers, assignment_id, question_id)

    testcases = _get_testcases(client, headers, assignment_id, question_id)
    for tc in testcases:
        resp = client.delete(
            f"/assignments/{assignment_id}/questions/{question_id}/testcases/{tc['id']}",
            headers=headers,
        )
        assert resp.status_code == 200

    resp = client.delete(
        f"/assignments/{assignment_id}/questions/{question_id}",
        headers=headers,
    )
    assert resp.status_code == 200


# ======================================================================
# 2. CASCADE: Delete assignment with questions (DB CASCADE on questions->assignments)
# ======================================================================


@pytest.mark.e2e
def test_delete_assignment_with_questions_cascades(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting an assignment should cascade-delete its questions."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "a_q")

    course_id = _create_course(client, headers, tag, "a_q")
    assignment_id = _create_assignment(client, headers, course_id, tag, "a_q")
    _create_question(client, headers, assignment_id)

    resp = client.delete(f"/assignments/{assignment_id}", headers=headers)
    assert (
        resp.status_code == 200
    ), f"Expected cascade delete to succeed, got {resp.status_code}"


@pytest.mark.e2e
def test_delete_assignment_with_questions_and_testcases_cascades(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting an assignment should cascade through questions and testcases."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "a_q_tc")

    course_id = _create_course(client, headers, tag, "a_q_tc")
    assignment_id = _create_assignment(client, headers, course_id, tag, "a_q_tc")
    question_id = _create_question(client, headers, assignment_id)
    _create_testcase(client, headers, assignment_id, question_id)

    resp = client.delete(f"/assignments/{assignment_id}", headers=headers)
    assert (
        resp.status_code == 200
    ), f"Expected deep cascade delete to succeed, got {resp.status_code}"


@pytest.mark.e2e
def test_delete_empty_assignment_succeeds(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting an assignment with no questions should succeed."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "a_empty")

    course_id = _create_course(client, headers, tag, "a_empty")
    assignment_id = _create_assignment(client, headers, course_id, tag, "a_empty")

    resp = client.delete(f"/assignments/{assignment_id}", headers=headers)
    assert resp.status_code == 200


# ======================================================================
# 3. CASCADE: Delete course with assignments (DB CASCADE on assignments->courses)
# ======================================================================


@pytest.mark.e2e
def test_delete_course_with_assignments_cascades(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a course should cascade-delete its assignments."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "c_a")

    course_id = _create_course(client, headers, tag, "c_a")
    _create_assignment(client, headers, course_id, tag, "c_a")

    resp = client.delete(f"/courses/{course_id}", headers=headers)
    assert (
        resp.status_code == 200
    ), f"Expected cascade delete to succeed, got {resp.status_code}"

    # Course should be gone
    resp = client.get(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.e2e
def test_delete_course_deep_chain_cascades(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a course should cascade through assignments -> questions -> testcases."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "c_deep")

    course_id = _create_course(client, headers, tag, "c_deep")
    assignment_id = _create_assignment(client, headers, course_id, tag, "c_deep")
    question_id = _create_question(client, headers, assignment_id)
    _create_testcase(client, headers, assignment_id, question_id)

    resp = client.delete(f"/courses/{course_id}", headers=headers)
    assert (
        resp.status_code == 200
    ), f"Expected deep cascade delete to succeed, got {resp.status_code}"

    # Course should be gone
    resp = client.get(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.e2e
def test_delete_empty_course_succeeds(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a course with no assignments should succeed."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "c_empty")

    course_id = _create_course(client, headers, tag, "c_empty")

    resp = client.delete(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 404


# ======================================================================
# 4. CASCADE: Delete course with enrolled students
#    (DB CASCADE on course_students -> courses)
# ======================================================================


@pytest.mark.e2e
def test_delete_course_with_enrolled_students_cascades(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a course should cascade-delete enrollment records in course_students."""
    tag = e2e_run_id
    _, inst_headers = _setup_instructor(client, tag, "c_enr")
    student_id, _, _ = _setup_student(client, tag, "c_enr")

    course_id = _create_course(client, inst_headers, tag, "c_enr")
    client.post(
        f"/courses/{course_id}/enroll/{student_id}", headers=inst_headers
    ).raise_for_status()

    resp = client.delete(f"/courses/{course_id}", headers=inst_headers)
    assert (
        resp.status_code == 200
    ), f"Expected cascade delete of course with enrollments to succeed, got {resp.status_code}"


@pytest.mark.e2e
def test_delete_course_after_unenrolling_students_succeeds(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a course succeeds once all students are unenrolled (manual cleanup still works)."""
    tag = e2e_run_id
    _, inst_headers = _setup_instructor(client, tag, "c_unenr")
    student_id, _, _ = _setup_student(client, tag, "c_unenr")

    course_id = _create_course(client, inst_headers, tag, "c_unenr")
    client.post(
        f"/courses/{course_id}/enroll/{student_id}", headers=inst_headers
    ).raise_for_status()
    client.delete(
        f"/courses/{course_id}/enroll/{student_id}", headers=inst_headers
    ).raise_for_status()

    resp = client.delete(f"/courses/{course_id}", headers=inst_headers)
    assert resp.status_code == 200


# ======================================================================
# 5. RESTRICT: Delete instructor who owns courses
#    (DB RESTRICT on courses.instructor_id -> users.id)
# ======================================================================


@pytest.mark.e2e
def test_delete_instructor_with_courses_blocked(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting an instructor who owns courses should be blocked (409 RESTRICT)."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "u_inst")

    _create_course(client, headers, tag, "u_inst")

    resp = client.delete("/users/me", headers=headers)
    assert (
        resp.status_code == 409
    ), f"Expected 409 Conflict (RESTRICT on courses.instructor_id), got {resp.status_code}"


@pytest.mark.e2e
def test_delete_instructor_without_courses_succeeds(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting an instructor with no courses should succeed."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "u_inst_clean")

    resp = client.delete("/users/me", headers=headers)
    assert resp.status_code == 200


# ======================================================================
# 6. CASCADE + RESTRICT: Delete student
#    course_students.student_id has CASCADE (enrollments removed)
#    submissions.student_id has RESTRICT (blocked if student has submissions)
# ======================================================================


@pytest.mark.e2e
def test_delete_enrolled_student_cascades_enrollment(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a student enrolled in a course should succeed (CASCADE on course_students)."""
    tag = e2e_run_id
    _, inst_headers = _setup_instructor(client, tag, "u_stu_enr")
    student_id, _, stu_headers = _setup_student(client, tag, "u_stu_enr")

    course_id = _create_course(client, inst_headers, tag, "u_stu_enr")
    client.post(
        f"/courses/{course_id}/enroll/{student_id}", headers=inst_headers
    ).raise_for_status()

    resp = client.delete("/users/me", headers=stu_headers)
    assert (
        resp.status_code == 200
    ), f"Expected student delete to cascade enrollment removal, got {resp.status_code}"


@pytest.mark.e2e
def test_delete_unenrolled_student_succeeds(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a student who is not enrolled in any course should succeed."""
    tag = e2e_run_id
    _, _, stu_headers = _setup_student(client, tag, "u_stu_clean")

    resp = client.delete("/users/me", headers=stu_headers)
    assert resp.status_code == 200


# ======================================================================
# 7. Manual bottom-up deletion still works (no regressions)
# ======================================================================


@pytest.mark.e2e
def test_manual_bottom_up_delete_full_chain(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Full bottom-up deletion: testcases -> questions -> assignment -> course."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "bottomup")

    course_id = _create_course(client, headers, tag, "bottomup")
    assignment_id = _create_assignment(client, headers, course_id, tag, "bottomup")
    q1_id = _create_question(client, headers, assignment_id)
    q2_id = _create_question(client, headers, assignment_id)
    _create_testcase(client, headers, assignment_id, q1_id)
    _create_testcase(client, headers, assignment_id, q1_id)
    _create_testcase(client, headers, assignment_id, q2_id)

    # Delete testcases
    for qid in [q1_id, q2_id]:
        for tc in _get_testcases(client, headers, assignment_id, qid):
            resp = client.delete(
                f"/assignments/{assignment_id}/questions/{qid}/testcases/{tc['id']}",
                headers=headers,
            )
            assert resp.status_code == 200

    # Delete questions
    for qid in [q1_id, q2_id]:
        resp = client.delete(
            f"/assignments/{assignment_id}/questions/{qid}",
            headers=headers,
        )
        assert resp.status_code == 200

    # Delete assignment
    resp = client.delete(f"/assignments/{assignment_id}", headers=headers)
    assert resp.status_code == 200

    # Delete course
    resp = client.delete(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 200

    # Verify gone
    resp = client.get(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 404


# ======================================================================
# 8. Multiple assignments -- deleting one shouldn't affect siblings
# ======================================================================


@pytest.mark.e2e
def test_delete_one_assignment_preserves_siblings(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting one empty assignment should not affect sibling assignments."""
    tag = e2e_run_id
    _, headers = _setup_instructor(client, tag, "sibling")

    course_id = _create_course(client, headers, tag, "sibling")
    a1 = _create_assignment(client, headers, course_id, tag, "sibling1")
    a2 = _create_assignment(client, headers, course_id, tag, "sibling2")

    resp = client.delete(f"/assignments/{a1}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/assignments/{a2}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/courses/{course_id}", headers=headers)
    assert resp.status_code == 200


# ======================================================================
# 9. Submission + cascade tests (requires MinIO -- skipped if unavailable)
# ======================================================================


def _create_submission(client, inst_headers, stu_headers, tag, suffix):
    """Helper: set up full chain and create a submission. Returns IDs or skips."""
    _, inst_headers_fresh = _setup_instructor(client, tag, suffix)
    student_id, _, stu_headers_fresh = _setup_student(client, tag, suffix)

    course_id = _create_course(client, inst_headers_fresh, tag, suffix)
    assignment_id = _create_assignment(
        client, inst_headers_fresh, course_id, tag, suffix
    )
    question_id = _create_question(client, inst_headers_fresh, assignment_id)

    client.post(
        f"/courses/{course_id}/enroll/{student_id}", headers=inst_headers_fresh
    ).raise_for_status()

    fake_file = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    resp = client.post(
        "/submissions/",
        data={"question_id": str(question_id), "assignment_id": str(assignment_id)},
        files={"file": ("test.png", fake_file, "image/png")},
        headers=stu_headers_fresh,
    )
    if resp.status_code != 200:
        pytest.skip(
            f"Submission creation failed ({resp.status_code}) -- MinIO may not be running"
        )

    submission_id = resp.json()["id"]
    return (
        course_id,
        assignment_id,
        question_id,
        submission_id,
        inst_headers_fresh,
        stu_headers_fresh,
    )


@pytest.mark.e2e
def test_delete_assignment_with_submission_cascades(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting an assignment that has submissions should cascade-delete them."""
    tag = e2e_run_id
    _, assignment_id, _, _, inst_headers, _ = _create_submission(
        client, None, None, tag, "a_sub"
    )

    resp = client.delete(f"/assignments/{assignment_id}", headers=inst_headers)
    assert (
        resp.status_code == 200
    ), f"Expected cascade delete of assignment with submissions to succeed, got {resp.status_code}"


@pytest.mark.e2e
def test_delete_question_with_submission_cascades(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a question that has submissions should cascade-delete them."""
    tag = e2e_run_id
    _, assignment_id, question_id, _, inst_headers, _ = _create_submission(
        client, None, None, tag, "q_sub"
    )

    resp = client.delete(
        f"/assignments/{assignment_id}/questions/{question_id}",
        headers=inst_headers,
    )
    assert (
        resp.status_code == 200
    ), f"Expected cascade delete of question with submissions to succeed, got {resp.status_code}"


@pytest.mark.e2e
def test_delete_submission_cascades_grade(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a submission should cascade-delete its grade (DB-level CASCADE)."""
    tag = e2e_run_id
    _, _, _, submission_id, inst_headers, stu_headers = _create_submission(
        client, None, None, tag, "sub_grade"
    )

    # Grade the submission
    resp = client.post(
        f"/grading/{submission_id}/grade",
        params={"final_grade": 85.0},
        headers=inst_headers,
    )
    if resp.status_code != 200:
        pytest.skip(f"Grade creation failed ({resp.status_code})")

    # Delete submission (student can delete their own)
    resp = client.delete(f"/submissions/{submission_id}", headers=stu_headers)
    assert (
        resp.status_code == 200
    ), f"Submission delete should cascade to grade (DB CASCADE). Got {resp.status_code}."

    # Submission should be gone
    resp = client.get(f"/submissions/{submission_id}", headers=inst_headers)
    assert resp.status_code == 404


# ======================================================================
# 10. RESTRICT: Delete student who has submissions
#     (DB RESTRICT on submissions.student_id -> users.id)
# ======================================================================


@pytest.mark.e2e
def test_delete_student_with_submissions_blocked(
    require_live_api: None, client: httpx.Client, e2e_run_id: str
) -> None:
    """Deleting a student who has submissions should be blocked (409 RESTRICT)."""
    tag = e2e_run_id
    _, _, _, _, _, stu_headers = _create_submission(client, None, None, tag, "stu_sub")

    resp = client.delete("/users/me", headers=stu_headers)
    assert (
        resp.status_code == 409
    ), f"Expected 409 Conflict (RESTRICT on submissions.student_id), got {resp.status_code}"
