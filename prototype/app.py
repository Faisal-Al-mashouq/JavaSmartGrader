from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path

from db import (
    create_assignment,
    create_submission,
    get_assignment,
    get_submission,
    init_db,
    list_assignments,
    list_submissions_by_assignment,
    update_submission,
)
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from services import grader_adapter, ocr_adapter, sandbox_adapter
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
ARTIFACTS_DIR = BASE_DIR / "artifacts"

load_dotenv(BASE_DIR / ".env")

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
init_db()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or "prototype-dev-key"

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".txt", ".java"}


def _allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _save_upload(file_storage) -> str:
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("No filename provided")
    if not _allowed_file(filename):
        raise ValueError("Unsupported file type")
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    target = UPLOADS_DIR / unique_name
    file_storage.save(target)
    return unique_name


def _normalize_rubric(raw_rubric: str) -> str:
    payload = json.loads(raw_rubric)
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _extract_score_fields(grade_payload: dict) -> tuple[float, float]:
    total = float(grade_payload.get("total_score", 0))
    max_score = float(grade_payload.get("max_score", 100))
    return total, max_score


def _write_artifact(submission_id: int, grade_payload: dict) -> None:
    artifact_path = ARTIFACTS_DIR / f"submission_{submission_id}_grade.json"
    artifact_path.write_text(
        json.dumps(grade_payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _build_timeline(status: str) -> list[dict[str, str]]:
    stages = ["Uploaded", "OCR", "Sandbox", "Grading", "Done"]
    state_map = {
        "Pending": ["current", "pending", "pending", "pending", "pending"],
        "OCR_Processing": ["complete", "current", "pending", "pending", "pending"],
        "Failed_OCR": ["complete", "failed", "pending", "pending", "pending"],
        "Sandbox_Processing": ["complete", "complete", "current", "pending", "pending"],
        "Grading_Processing": [
            "complete",
            "complete",
            "complete",
            "current",
            "pending",
        ],
        "Done": ["complete", "complete", "complete", "complete", "complete"],
        "Failed": ["complete", "complete", "complete", "failed", "pending"],
    }
    states = state_map.get(
        status, ["pending", "pending", "pending", "pending", "pending"]
    )
    return [
        {"name": stage, "state": state}
        for stage, state in zip(stages, states, strict=False)
    ]


def _run_pipeline(submission_id: int) -> None:
    try:
        submission = get_submission(submission_id)
        if submission is None:
            return

        assignment = get_assignment(submission["assignment_id"])
        if assignment is None:
            update_submission(submission_id, status="Failed")
            return

        typed_code = (submission.get("typed_code") or "").strip()
        code_text = typed_code

        if typed_code:
            update_submission(
                submission_id,
                status="Sandbox_Processing",
                ocr_text=typed_code,
                ocr_confidence=1.0,
            )
        else:
            update_submission(submission_id, status="OCR_Processing")
            ocr_result = ocr_adapter.extract_text(submission.get("upload_path") or "")
            code_text = (ocr_result.get("text") or "").strip()
            confidence = float(ocr_result.get("confidence") or 0.0)

            if not code_text or confidence < 0.55:
                update_submission(
                    submission_id,
                    status="Failed_OCR",
                    ocr_text=code_text,
                    ocr_confidence=confidence,
                )
                return

            update_submission(
                submission_id,
                status="Sandbox_Processing",
                ocr_text=code_text,
                ocr_confidence=confidence,
            )

        sandbox_result = sandbox_adapter.run(code_text)
        sandbox_logs = sandbox_result.get("logs") or ""
        update_submission(
            submission_id,
            status="Grading_Processing",
            sandbox_logs=sandbox_logs,
        )

        rubric_json = assignment.get("rubric_json") or "{}"
        grade_payload = grader_adapter.grade(code_text, rubric_json, sandbox_logs)
        total_score, max_score = _extract_score_fields(grade_payload)

        update_submission(
            submission_id,
            status="Done",
            grade_json=json.dumps(grade_payload, ensure_ascii=True, indent=2),
            grade_score=total_score,
            grade_max=max_score,
        )
        _write_artifact(submission_id, grade_payload)
    except Exception as exc:
        existing = get_submission(submission_id) or {}
        existing_logs = existing.get("sandbox_logs") or ""
        merged_logs = f"{existing_logs}\n\n[Pipeline Error]\n{exc}".strip()
        update_submission(submission_id, status="Failed", sandbox_logs=merged_logs)


def _start_pipeline(submission_id: int) -> None:
    worker = threading.Thread(
        target=_run_pipeline,
        args=(submission_id,),
        daemon=True,
    )
    worker.start()


@app.route("/")
def index():
    return redirect(url_for("instructor_dashboard"))


@app.route("/instructor")
def instructor_dashboard():
    assignments = list_assignments()
    return render_template("instructor_dashboard.html", assignments=assignments)


@app.route("/instructor/assignments/new", methods=["GET", "POST"])
def create_assignment_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        rubric_json = request.form.get("rubric_json", "").strip()

        if not name:
            flash("Assignment name is required.", "error")
            return redirect(url_for("create_assignment_page"))

        try:
            normalized_rubric = _normalize_rubric(rubric_json or "{}")
        except json.JSONDecodeError:
            flash("Rubric must be valid JSON.", "error")
            return redirect(url_for("create_assignment_page"))

        assignment_id = create_assignment(
            name=name,
            description=description,
            rubric_json=normalized_rubric,
        )
        flash("Assignment created.", "success")
        return redirect(url_for("assignment_detail", assignment_id=assignment_id))

    return render_template("create_assignment.html")


@app.route("/instructor/assignments/<int:assignment_id>")
def assignment_detail(assignment_id: int):
    assignment = get_assignment(assignment_id)
    if assignment is None:
        abort(404)
    submissions = list_submissions_by_assignment(assignment_id)
    return render_template(
        "assignment_detail.html",
        assignment=assignment,
        submissions=submissions,
    )


@app.route("/instructor/assignments/<int:assignment_id>/load-demo", methods=["POST"])
def load_demo_set(assignment_id: int):
    assignment = get_assignment(assignment_id)
    if assignment is None:
        abort(404)

    demo_inputs = [
        ("High", request.files.get("high_file")),
        ("Mid", request.files.get("mid_file")),
        ("Low", request.files.get("low_file")),
    ]

    created = 0
    for label, file_storage in demo_inputs:
        if file_storage is None or not file_storage.filename:
            continue
        try:
            upload_name = _save_upload(file_storage)
        except ValueError as exc:
            flash(f"{label} demo skipped: {exc}", "error")
            continue

        submission_id = create_submission(
            assignment_id=assignment_id,
            label=label,
            upload_path=upload_name,
            typed_code=None,
            status="Pending",
        )
        _start_pipeline(submission_id)
        created += 1

    flash(f"Demo submissions queued: {created}", "success")
    return redirect(url_for("assignment_detail", assignment_id=assignment_id))


@app.route("/student")
def student_dashboard():
    assignments = list_assignments()
    return render_template("student_dashboard.html", assignments=assignments)


@app.route("/student/assignments/<int:assignment_id>/submit", methods=["GET", "POST"])
def submit_assignment(assignment_id: int):
    assignment = get_assignment(assignment_id)
    if assignment is None:
        abort(404)

    if request.method == "POST":
        typed_code = request.form.get("typed_code", "").strip() or None
        file_storage = request.files.get("upload_file")
        upload_name = None

        if file_storage and file_storage.filename:
            try:
                upload_name = _save_upload(file_storage)
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(
                    url_for("submit_assignment", assignment_id=assignment_id)
                )

        if not typed_code and not upload_name:
            flash("Provide either a file upload or typed code.", "error")
            return redirect(url_for("submit_assignment", assignment_id=assignment_id))

        submission_id = create_submission(
            assignment_id=assignment_id,
            label=None,
            upload_path=upload_name,
            typed_code=typed_code,
            status="Pending",
        )
        _start_pipeline(submission_id)
        flash("Submission accepted. Processing started.", "success")
        return redirect(url_for("submission_detail", submission_id=submission_id))

    return render_template("submit.html", assignment=assignment)


@app.route("/submissions/<int:submission_id>")
def submission_detail(submission_id: int):
    submission = get_submission(submission_id)
    if submission is None:
        abort(404)

    assignment = get_assignment(submission["assignment_id"])
    if assignment is None:
        abort(404)

    upload_name = submission.get("upload_path") or ""
    suffix = Path(upload_name).suffix.lower()
    is_image = suffix in {".png", ".jpg", ".jpeg", ".webp"}
    is_pdf = suffix == ".pdf"

    grade_json_pretty = submission.get("grade_json") or ""
    if grade_json_pretty:
        try:
            grade_json_pretty = json.dumps(json.loads(grade_json_pretty), indent=2)
        except json.JSONDecodeError:
            pass

    timeline = _build_timeline(submission.get("status") or "Pending")
    return render_template(
        "submission_detail.html",
        assignment=assignment,
        submission=submission,
        timeline=timeline,
        is_image=is_image,
        is_pdf=is_pdf,
        grade_json_pretty=grade_json_pretty,
    )


@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(UPLOADS_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
