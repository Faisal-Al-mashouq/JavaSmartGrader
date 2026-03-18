from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "prototype.db"


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assignment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                rubric_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submission (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                label TEXT,
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL,
                upload_path TEXT,
                typed_code TEXT,
                ocr_text TEXT,
                ocr_confidence REAL,
                sandbox_logs TEXT,
                grade_json TEXT,
                grade_score REAL,
                grade_max REAL,
                FOREIGN KEY (assignment_id) REFERENCES assignment (id)
            )
            """)
        conn.commit()


def create_assignment(*, name: str, description: str, rubric_json: str) -> int:
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO assignment (name, description, rubric_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, rubric_json, _utcnow_iso()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_assignments() -> list[dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM assignment ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_assignment(assignment_id: int) -> dict[str, Any] | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM assignment WHERE id = ?",
            (assignment_id,),
        ).fetchone()
    return _row_to_dict(row)


def create_submission(
    *,
    assignment_id: int,
    label: str | None,
    upload_path: str | None,
    typed_code: str | None,
    status: str,
) -> int:
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO submission (
                assignment_id,
                label,
                submitted_at,
                status,
                upload_path,
                typed_code
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                assignment_id,
                label,
                _utcnow_iso(),
                status,
                upload_path,
                typed_code,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_submission(submission_id: int) -> dict[str, Any] | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM submission WHERE id = ?",
            (submission_id,),
        ).fetchone()
    return _row_to_dict(row)


def list_submissions_by_assignment(assignment_id: int) -> list[dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM submission
            WHERE assignment_id = ?
            ORDER BY submitted_at DESC
            """,
            (assignment_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_submission(submission_id: int, **fields: Any) -> None:
    if not fields:
        return

    columns = ", ".join([f"{key} = ?" for key in fields.keys()])
    values = list(fields.values())
    values.append(submission_id)

    with _get_conn() as conn:
        conn.execute(
            f"UPDATE submission SET {columns} WHERE id = ?",
            tuple(values),
        )
        conn.commit()
