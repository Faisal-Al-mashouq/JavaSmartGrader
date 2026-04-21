"""Second E2E driver: pauses at awaiting_student_approval, queries the DB to
print the actual confidence_flags rows the student would see, then approves
and reprints the rows to confirm they're deleted.

Runs inside the backend container. Uses db.session for live DB inspection.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from io import BytesIO

import httpx
from api.s3 import get_file
from db.session import async_session
from sqlalchemy import text

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
    'System.out.println("approved"); } }'
)


async def dump_flags(submission_id: int, label: str) -> None:
    async with async_session() as s:
        rows = await s.execute(
            text("""
                SELECT cf.id,
                        cf.transcription_id,
                        cf.text_segment,
                        cf.confidence_score,
                        cf.coordinates,
                        cf.suggestions
                FROM confidence_flags cf
                JOIN transcriptions t ON t.id = cf.transcription_id
                WHERE t.submission_id = :sid
                ORDER BY cf.id
                """),
            {"sid": submission_id},
        )
        rs = rows.fetchall()
        print(f"  --- confidence_flags @ {label} (submission_id={submission_id}) ---")
        print(f"      count = {len(rs)}")
        for r in rs:
            print(
                f"      id={r[0]} tid={r[1]} "
                f"text_segment={r[2]!r} score={r[3]} "
                f"coords={r[4]!r} suggestions={r[5]!r}"
            )
        rows = await s.execute(
            text("""
                SELECT id, transcribed_text
                FROM transcriptions
                WHERE submission_id = :sid
                """),
            {"sid": submission_id},
        )
        tr = rows.fetchone()
        if tr:
            snippet = (tr[1] or "")[:120]
            print(f"      transcription.id={tr[0]} text[:120]={snippet!r}")


def main_sync():
    print(f"=== run_id={RUN_ID}, base={BASE} ===")
    student = {
        "username": f"e2e_stu2_{RUN_ID}",
        "password": "pw123",
        "email": f"stu2_{RUN_ID}@t.local",
    }
    instructor = {
        "username": f"e2e_ins2_{RUN_ID}",
        "password": "pw123",
        "email": f"ins2_{RUN_ID}@t.local",
    }

    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        for u, role in [(student, "student"), (instructor, "instructor")]:
            r = client.post(
                "/users/register",
                json={
                    "username": u["username"],
                    "password": u["password"],
                    "email": u["email"],
                    "role": role,
                },
            )
            r.raise_for_status()
        stu_tok = client.post(
            "/users/login",
            data={"username": student["username"], "password": student["password"]},
        ).json()["access_token"]
        ins_tok = client.post(
            "/users/login",
            data={
                "username": instructor["username"],
                "password": instructor["password"],
            },
        ).json()["access_token"]
        sh = {"Authorization": f"Bearer {stu_tok}"}
        ih = {"Authorization": f"Bearer {ins_tok}"}
        stu_id = client.get("/users/me", headers=sh).json()["id"]

        course_id = client.post(
            "/courses/",
            params={"name": f"E2E2 {RUN_ID}", "description": "E2E2"},
            headers=ih,
        ).json()["id"]
        assn_id = client.post(
            "/assignments/",
            params={
                "course_id": course_id,
                "title": f"Assn2 {RUN_ID}",
                "description": "E2E2",
            },
            json=RUBRIC,
            headers=ih,
        ).json()["id"]
        q_id = client.post(
            f"/assignments/{assn_id}/questions/",
            params={"question_text": QUESTION_TEXT},
            headers=ih,
        ).json()["id"]
        client.post(f"/courses/{course_id}/enroll/{stu_id}", headers=ih)

        print("[A] submit image")
        img = get_file(IMAGE_KEY)
        r = client.post(
            "/submissions/",
            data={"question_id": str(q_id), "assignment_id": str(assn_id)},
            headers=sh,
            files={"file": ("page.png", BytesIO(img), "image/png")},
        )
        r.raise_for_status()
        sub_id = r.json()["id"]
        print(f"    submission_id={sub_id}")

        print("[B] poll for awaiting_student_approval")
        deadline = time.time() + 180
        last = None
        while time.time() < deadline:
            s = client.get(f"/submissions/{sub_id}", headers=sh).json()["state"]
            if s != last:
                print(f"    state -> {s}")
                last = s
            if s == "awaiting_student_approval":
                break
            if s in ("failed", "graded"):
                break
            time.sleep(3)

        print("[C] inspect DB flags at pause")
        asyncio.run(dump_flags(sub_id, "awaiting_student_approval"))

        print("[D] GET /pending-review response body")
        pr = client.get(f"/submissions/{sub_id}/pending-review", headers=sh).json()
        print(f"    transcribed_text snippet = {pr['transcribed_text'][:160]!r}")
        print(f"    flags.count              = {len(pr['flags'])}")
        for i, f in enumerate(pr["flags"]):
            print(
                f"    flags[{i}] = id={f['id']} "
                f"text_segment={f['text_segment']!r} "
                f"score={f['confidence_score']} "
                f"coords={f.get('coordinates')!r} "
                f"suggestions={f.get('suggestions')!r}"
            )

        print("[E] approve with cleaned-up Java")
        r = client.post(
            f"/submissions/{sub_id}/approve-transcription",
            json={"approved_text": APPROVED_CODE},
            headers=sh,
        )
        r.raise_for_status()
        print(f"    {r.json()}")

        print("[F] inspect DB flags after approval")
        asyncio.run(dump_flags(sub_id, "after-approval"))

        print("[G] poll for final state")
        deadline = time.time() + 180
        last = None
        final = None
        while time.time() < deadline:
            final = client.get(f"/submissions/{sub_id}", headers=sh).json()["state"]
            if final != last:
                print(f"    state -> {final}")
                last = final
            if final in ("graded", "failed"):
                break
            time.sleep(3)

        print(
            f"\n=== DONE run_id={RUN_ID} submission_id={sub_id} "
            f"final_state={final} ==="
        )


if __name__ == "__main__":
    main_sync()
