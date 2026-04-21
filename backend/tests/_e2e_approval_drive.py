"""One-off driver for manual E2E verification of the student-approval endpoints.

Runs inside the backend container so it has S3 creds + access to api.s3.get_file.
NOT a pytest test. Delete after verification.
"""

from __future__ import annotations

import os
import time
import uuid
from io import BytesIO

import httpx
from api.s3 import get_file

BASE = os.environ.get("E2E_API_BASE", "http://localhost:8000").rstrip("/")
IMAGE_KEY = "submissions/1/page.png"
RUBRIC = {
    "criteria": {
        "Correctness": {"weight": 100, "description": "Correct"},
        "Code Quality": {"weight": 100, "description": "Code Quality"},
    }
}
QUESTION_TEXT = "Write a simple Java program."
RUN_ID = uuid.uuid4().hex[:10]
APPROVED_CODE = (
    "public class Foo { "
    "public static void main(String[] args) { "
    'System.out.println("hi"); } }'
)


def _post(client, url, **kw):
    r = client.post(url, **kw)
    if r.status_code >= 400:
        print(f"  POST {url} -> {r.status_code}: {r.text[:200]}")
    r.raise_for_status()
    return r


def _get(client, url, headers=None):
    r = client.get(url, headers=headers)
    if r.status_code >= 400:
        print(f"  GET {url} -> {r.status_code}: {r.text[:200]}")
    r.raise_for_status()
    return r


def _register(client, *, username, password, email, role):
    client.post(
        "/users/register",
        json={
            "username": username,
            "password": password,
            "email": email,
            "role": role,
        },
    ).raise_for_status()


def _login(client, *, username, password):
    r = client.post("/users/login", data={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    print(f"=== run_id={RUN_ID}, base={BASE} ===")
    student = {
        "username": f"e2e_stu_{RUN_ID}",
        "password": "pw123",
        "email": f"stu_{RUN_ID}@t.local",
    }
    instructor = {
        "username": f"e2e_ins_{RUN_ID}",
        "password": "pw123",
        "email": f"ins_{RUN_ID}@t.local",
    }
    other_student = {
        "username": f"e2e_other_{RUN_ID}",
        "password": "pw123",
        "email": f"other_{RUN_ID}@t.local",
    }

    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        print("[1] register student + instructor + other_student")
        _register(client, **student, role="student")
        _register(client, **instructor, role="instructor")
        _register(client, **other_student, role="student")

        print("[2] login")
        stu_tok = _login(
            client, username=student["username"], password=student["password"]
        )
        ins_tok = _login(
            client, username=instructor["username"], password=instructor["password"]
        )
        other_tok = _login(
            client,
            username=other_student["username"],
            password=other_student["password"],
        )
        sh = {"Authorization": f"Bearer {stu_tok}"}
        ih = {"Authorization": f"Bearer {ins_tok}"}
        oh = {"Authorization": f"Bearer {other_tok}"}

        stu_id = _get(client, "/users/me", headers=sh).json()["id"]
        print(f"    student id={stu_id}")

        print("[3] create course / assignment / question / enroll")
        course_id = _post(
            client,
            "/courses/",
            params={"name": f"E2E {RUN_ID}", "description": "E2E"},
            headers=ih,
        ).json()["id"]
        assn_id = _post(
            client,
            "/assignments/",
            params={
                "course_id": course_id,
                "title": f"Assn {RUN_ID}",
                "description": "E2E",
            },
            json=RUBRIC,
            headers=ih,
        ).json()["id"]
        q_id = _post(
            client,
            f"/assignments/{assn_id}/questions/",
            params={"question_text": QUESTION_TEXT},
            headers=ih,
        ).json()["id"]
        r = client.post(f"/courses/{course_id}/enroll/{stu_id}", headers=ih)
        assert r.status_code in (200, 201, 409), r.text
        print(f"    course={course_id} assn={assn_id} q={q_id}")

        print("[4] submit image")
        img = get_file(IMAGE_KEY)
        r = _post(
            client,
            "/submissions/",
            data={"question_id": str(q_id), "assignment_id": str(assn_id)},
            headers=sh,
            files={"file": ("page.png", BytesIO(img), "image/png")},
        )
        sub = r.json()
        sub_id = sub["id"]
        print(f"    submission_id={sub_id} initial state={sub['state']}")

        print(
            "[5] poll for awaiting_student_approval "
            "(timeout 180s; OCR+LLM can take a while)"
        )
        deadline = time.time() + 180
        state = sub["state"]
        last_state = state
        while time.time() < deadline:
            r = _get(client, f"/submissions/{sub_id}", headers=sh)
            state = r.json()["state"]
            if state != last_state:
                print(f"    state -> {state}")
                last_state = state
            if state == "awaiting_student_approval":
                break
            if state in ("failed", "graded"):
                print(f"  !! unexpected terminal state {state} before approval")
                break
            time.sleep(3)
        assert (
            state == "awaiting_student_approval"
        ), f"expected awaiting_student_approval, got {state}"
        print("    confirmed pause at awaiting_student_approval")

        print("[6] GET /pending-review happy path (owner)")
        r = _get(client, f"/submissions/{sub_id}/pending-review", headers=sh)
        pr = r.json()
        print(
            f"    transcribed_text={pr['transcribed_text']!r} "
            f"flags_count={len(pr['flags'])}"
        )
        tid = pr["transcription_id"]

        print("[7] GET /pending-review gate: non-owner -> 403")
        r = client.get(f"/submissions/{sub_id}/pending-review", headers=oh)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        print("    ok (403)")

        print("[8] GET /pending-review gate: not-found -> 404")
        r = client.get("/submissions/999999/pending-review", headers=sh)
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"
        print("    ok (404)")

        print("[9] POST /approve-transcription gate: empty text -> 422")
        r = client.post(
            f"/submissions/{sub_id}/approve-transcription",
            json={"approved_text": ""},
            headers=sh,
        )
        assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"
        print("    ok (422)")

        print("[10] POST /approve-transcription gate: non-owner -> 403")
        r = client.post(
            f"/submissions/{sub_id}/approve-transcription",
            json={"approved_text": APPROVED_CODE},
            headers=oh,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        print("    ok (403)")

        print("[11] POST /approve-transcription gate: instructor -> 403")
        r = client.post(
            f"/submissions/{sub_id}/approve-transcription",
            json={"approved_text": APPROVED_CODE},
            headers=ih,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        print("    ok (403)")

        print("[12] POST /approve-transcription happy path (owner)")
        r = _post(
            client,
            f"/submissions/{sub_id}/approve-transcription",
            json={"approved_text": APPROVED_CODE},
            headers=sh,
        )
        print(f"    {r.json()}")

        print("[13] GET /pending-review after approval -> 409 (not awaiting)")
        r = client.get(f"/submissions/{sub_id}/pending-review", headers=sh)
        assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"
        print(f"    ok (409): {r.json().get('detail','')}")

        print("[14] poll for final state (processing -> graded), timeout 180s")
        deadline = time.time() + 180
        state = None
        last_state = None
        while time.time() < deadline:
            r = _get(client, f"/submissions/{sub_id}", headers=sh)
            state = r.json()["state"]
            if state != last_state:
                print(f"    state -> {state}")
                last_state = state
            if state in ("graded", "failed"):
                break
            time.sleep(3)
        print(f"    final state = {state}")

        print("[15] POST /approve-transcription gate: now graded -> 409")
        r = client.post(
            f"/submissions/{sub_id}/approve-transcription",
            json={"approved_text": APPROVED_CODE},
            headers=sh,
        )
        assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text}"
        print("    ok (409)")

        print(
            f"\n=== DONE run_id={RUN_ID} submission_id={sub_id} "
            f"transcription_id={tid} final_state={state} ==="
        )


if __name__ == "__main__":
    main()
