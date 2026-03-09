"""E2E test: register, create course/assignment/question, submit.
Run: uv run python -m api.test_job
"""

import asyncio

from httpx import AsyncClient

BASE = "http://localhost:8000"
STUDENT = {
    "username": "test_student",
    "password": "testpass123",
    "email": "test@test.com",
}
INSTRUCTOR = {
    "username": "test_instructor",
    "password": "testpass123",
    "email": "inst@test.com",
}
RUBRIC = {"criteria": {"Correctness": {"weight": 100, "description": "Correct"}}}


async def main() -> None:
    async with AsyncClient(base_url=BASE, timeout=30.0) as client:
        await client.post("/users/register", json={**STUDENT, "role": "student"})
        await client.post("/users/register", json={**INSTRUCTOR, "role": "instructor"})

        student_login = await client.post(
            "/users/login",
            data={"username": STUDENT["username"], "password": STUDENT["password"]},
        )
        student_login.raise_for_status()
        student_token = student_login.json()["access_token"]

        instructor_login = await client.post(
            "/users/login",
            data={
                "username": INSTRUCTOR["username"],
                "password": INSTRUCTOR["password"],
            },
        )
        instructor_login.raise_for_status()
        instructor_token = instructor_login.json()["access_token"]
        inst_headers = {"Authorization": f"Bearer {instructor_token}"}

        course = await client.post(
            "/courses/",
            params={"name": "Test Course", "description": "E2E"},
            headers=inst_headers,
        )
        if course.status_code == 400 and "already exists" in (
            course.json().get("detail") or ""
        ):
            my_courses = await client.get("/courses/me", headers=inst_headers)
            my_courses.raise_for_status()
            existing = next(
                (c for c in my_courses.json() if c["name"] == "Test Course"), None
            )
            if not existing:
                course.raise_for_status()
            course_id = existing["id"]
        else:
            course.raise_for_status()
            course_id = course.json()["id"]

        assignment = await client.post(
            "/assignments/",
            params={
                "course_id": course_id,
                "title": "Test Assignment",
                "description": "E2E",
            },
            json=RUBRIC,
            headers=inst_headers,
        )
        assignment.raise_for_status()
        assignment_id = assignment.json()["id"]

        question = await client.post(
            f"/assignments/{assignment_id}/questions/",
            params={"question_text": "Print Hello World"},
            headers=inst_headers,
        )
        question.raise_for_status()
        question_id = question.json()["id"]

        me = await client.get(
            "/users/me", headers={"Authorization": f"Bearer {student_token}"}
        )
        me.raise_for_status()
        student_id = me.json()["id"]

        enroll = await client.post(
            f"/courses/{course_id}/enroll/{student_id}",
            headers=inst_headers,
        )
        if enroll.status_code not in (200, 201, 409):
            enroll.raise_for_status()

        resp = await client.post(
            "/submissions/",
            params={
                "question_id": question_id,
                "assignment_id": assignment_id,
                "image_url": "https://example.com/img.jpg",
            },
            headers={"Authorization": f"Bearer {student_token}"},
        )
        resp.raise_for_status()
        print("Submission created:", resp.json()["id"])


if __name__ == "__main__":
    asyncio.run(main())
