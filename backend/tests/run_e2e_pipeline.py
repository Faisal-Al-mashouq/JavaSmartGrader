"""Run the full E2E pipeline with a chosen image and display results.

Usage::

    uv run python tests/run_e2e_pipeline.py <image_path>

    # Override API base URL (default: http://localhost:8000)
    uv run python tests/run_e2e_pipeline.py <image_path> --api-base http://localhost:8000

    # Adjust how long to wait for pipeline completion (default: 120s)
    uv run python tests/run_e2e_pipeline.py <image_path> --timeout 180

    # Skip worker restart (if workers already running and up to date)
    uv run python tests/run_e2e_pipeline.py <image_path> --no-restart-workers

Requires Redis, PostgreSQL, and S3 to be running.
The script will auto-start the API and workers if not already running.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from io import BytesIO
from pathlib import Path

import httpx
import redis

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_API_BASE = "http://localhost:8000"
DEFAULT_REDIS_URL = "redis://localhost:6379"
DEFAULT_TIMEOUT = 120  # seconds to wait for pipeline to finish
POLL_INTERVAL = 3  # seconds between status polls
WORKER_STARTUP_WAIT = 5  # seconds to wait for workers to initialize

# Environment overrides so workers connect to localhost (not Docker hostnames)
WORKER_ENV_OVERRIDES = {
    "APP_ENV": "dev",
    "ASYNC_DATABASE_URL": "postgresql+asyncpg://jsg_user:jsg_secure_password@localhost:5432/jsg_db",
    "DATABASE_URL": "postgresql://jsg_user:jsg_secure_password@localhost:5432/jsg_db",
    "REDIS_ENDPOINT": "redis://localhost:6379",
}

RUBRIC = {
    "criteria": {
        "Correctness": {"weight": 100, "description": "Correct"},
        "Code Quality": {"weight": 100, "description": "Code Quality"},
    }
}
QUESTION_TEXT = "write a two java statements that calls the  "

S3_IMAGE_KEY = "submissions/1/page.png"
COMPLETED_QUEUE = "jsg.v1:MainJobQueue:completed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _header(title: str) -> str:
    bar = "=" * 60
    return f"\n{bar}\n  {title}\n{bar}"


def _sub_header(title: str) -> str:
    return f"\n--- {title} ---"


def _json_pretty(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


def _upload_image_to_s3(image_path: str) -> None:
    """Upload the local image to S3 at the key the test expects."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from settings import s3_client, settings

    print(f"  Uploading '{image_path}' -> s3://{settings.s3_bucket}/{S3_IMAGE_KEY}")
    s3_client.upload_file(image_path, settings.s3_bucket, S3_IMAGE_KEY)
    print("  Upload complete.")


def _build_worker_env() -> dict:
    """Build environment for worker subprocesses with localhost overrides."""
    env = os.environ.copy()
    env.update(WORKER_ENV_OVERRIDES)
    return env


def _kill_workers(procs: list[subprocess.Popen]) -> None:
    """Terminate all worker subprocesses."""
    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
    # Give them a moment to exit cleanly, then force-kill
    deadline = time.time() + 5
    for proc in procs:
        remaining = max(0.0, deadline - time.time())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            proc.kill()


def _start_workers(backend_dir: Path) -> list[subprocess.Popen]:
    """Start the API server + OCR, sandbox, and AI grader workers as subprocesses."""
    env = _build_worker_env()
    uv = "uv"

    # Redirect stdout/stderr to DEVNULL so they don't clutter the test output.
    # Change to PIPE if you want to capture worker logs.
    sink = subprocess.DEVNULL

    procs = []

    # API server
    procs.append(
        subprocess.Popen(
            [uv, "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=backend_dir,
            env=env,
            stdout=sink,
            stderr=sink,
        )
    )

    # OCR worker
    procs.append(
        subprocess.Popen(
            [uv, "run", "python", "-m", "ocr.main"],
            cwd=backend_dir,
            env=env,
            stdout=sink,
            stderr=sink,
        )
    )

    # Sandbox worker
    procs.append(
        subprocess.Popen(
            [uv, "run", "python", "-m", "sandbox.sandbox_worker"],
            cwd=backend_dir,
            env=env,
            stdout=sink,
            stderr=sink,
        )
    )

    # AI grader worker
    procs.append(
        subprocess.Popen(
            [uv, "run", "python", "-m", "ai_grader.main"],
            cwd=backend_dir,
            env=env,
            stdout=sink,
            stderr=sink,
        )
    )

    return procs


def _kill_existing_workers() -> None:
    """Kill any previously running uvicorn / worker processes by name."""
    is_windows = sys.platform == "win32"
    # Patterns to match in the command line
    patterns = [
        "uvicorn main:app",
        "ocr.main",
        "sandbox.sandbox_worker",
        "ai_grader.main",
    ]
    if is_windows:
        try:
            import psutil

            for proc in psutil.process_iter(["pid", "cmdline"]):
                try:
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    if any(p in cmdline for p in patterns):
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            # psutil not available — best-effort via taskkill on uvicorn
            subprocess.run(
                ["taskkill", "/F", "/IM", "uvicorn.exe"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    else:
        for pattern in patterns:
            subprocess.run(
                ["pkill", "-f", pattern],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


def _clear_stale_redis_jobs(redis_url: str) -> None:
    """Delete the processing queue so stale jobs don't block new ones."""
    r = redis.from_url(redis_url)
    processing_key = "jsg.v1:MainJobQueue:processing"
    deleted = r.delete(processing_key)
    if deleted:
        print(f"  Cleared stale Redis processing queue: {processing_key}")


def _wait_for_api(api_base: str, timeout: int = 30) -> bool:
    """Poll until the API responds or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{api_base}/openapi.json", timeout=3.0)
            if r.status_code == 200:
                return True
        except (httpx.HTTPError, OSError):
            pass
        time.sleep(1)
    return False


def _register(
    client: httpx.Client, *, username: str, password: str, email: str, role: str
):
    r = client.post(
        "/users/register",
        json={"username": username, "password": password, "email": email, "role": role},
    )
    if r.status_code == 409:
        return
    r.raise_for_status()


def _login(client: httpx.Client, *, username: str, password: str) -> str:
    r = client.post("/users/login", data={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _find_job_result(redis_url: str, submission_id: int) -> dict | None:
    """Search the Redis completed queue for the job matching this submission."""
    r = redis.from_url(redis_url)
    items = r.lrange(COMPLETED_QUEUE, 0, -1)
    for raw in items:
        try:
            job = json.loads(raw)
            if job.get("initial_request", {}).get("submission_id") == submission_id:
                return job
        except (json.JSONDecodeError, KeyError):
            continue
    return None


def _extract_ocr_data(job_result: dict) -> tuple[dict | None, dict | None]:
    """Extract ocr_result and llm_result from the job result payload."""
    for entry in job_result.get("job_result_payload", []):
        jr = entry.get("job_result", {})
        if jr.get("type") == "OCR":
            result = jr.get("result", {}).get("result", {})
            return result.get("ocr_result"), result.get("llm_result")
    return None, None


def _extract_sandbox_data(job_result: dict) -> dict | None:
    """Extract sandbox result from the job result payload."""
    for entry in job_result.get("job_result_payload", []):
        jr = entry.get("job_result", {})
        if jr.get("type") == "SANDBOX":
            return jr.get("result", {}).get("result")
    return None


def _extract_grader_data(job_result: dict) -> dict | None:
    """Extract grader result from the job result payload."""
    for entry in job_result.get("job_result_payload", []):
        jr = entry.get("job_result", {})
        if jr.get("type") == "GRADER":
            return jr
    return None


def _print_ocr_results(ocr_result: dict | None, llm_result: dict | None) -> None:
    """Print raw OCR extraction and LLM correction side by side."""

    # -- Raw OCR --
    print(_sub_header("Stage 1a: OCR Extraction (Azure)"))
    if ocr_result is None:
        print("  No OCR extraction result found.")
        return

    print(f"  Success: {ocr_result.get('success')}")

    raw_text = ocr_result.get("raw_text")
    if raw_text:
        print("\n  Raw OCR Text:")
        for line in raw_text.split("\n"):
            print(f"    | {line}")

    annotated = ocr_result.get("annotated_text")
    if annotated:
        print("\n  Annotated Text (word[confidence%]):")
        for line in annotated.split("\n"):
            print(f"    | {line}")

    lines = ocr_result.get("lines", [])
    if lines:
        print("\n  Word-Level Confidence:")
        print(f"    {'Word':<20} {'Confidence':>10}")
        print(f"    {'-'*20} {'-'*10}")
        for line_data in lines:
            for word in line_data.get("words", []):
                conf = word["confidence"]
                marker = " <-- LOW" if conf < 0.5 else ""
                print(f"    {word['content']:<20} {conf*100:>9.1f}%{marker}")

    if ocr_result.get("errors"):
        print(f"\n  Errors: {ocr_result['errors']}")

    # -- LLM Correction --
    print(_sub_header("Stage 1b: LLM Correction (Gemini)"))
    if llm_result is None:
        print("  No LLM correction result found.")
        return

    print(f"  Success:    {llm_result.get('success')}")
    print(f"  Model Used: {llm_result.get('model_used', 'N/A')}")

    corrected = llm_result.get("corrected_code")
    if corrected:
        print("\n  Corrected Code:")
        for line in corrected.split("\n"):
            print(f"    | {line}")
    else:
        print("\n  Corrected Code: (none — LLM correction failed or returned empty)")

    uncertain = llm_result.get("uncertain_words")
    if uncertain:
        print(f"\n  Uncertain Words ({len(uncertain)}):")
        for uw in uncertain:
            print(
                f"    - '{uw['original_word']}' (conf={uw['confidence_pct']}%, "
                f"pos={uw['coordinates']}) suggestions={uw['suggestions']}"
            )

    if llm_result.get("errors"):
        print("\n  Errors:")
        for err in llm_result["errors"]:
            print(f"    - {err}")

    # -- Comparison --
    if raw_text and corrected:
        print(_sub_header("OCR vs LLM Comparison"))
        print("  Raw OCR Text:")
        for line in raw_text.split("\n"):
            print(f"    | {line}")
        print("\n  LLM Corrected Code:")
        for line in corrected.split("\n"):
            print(f"    | {line}")
    elif raw_text and not corrected:
        print(_sub_header("OCR vs LLM Comparison"))
        print("  Raw OCR Text:")
        for line in raw_text.split("\n"):
            print(f"    | {line}")
        print("\n  LLM Corrected Code: UNAVAILABLE (correction failed)")
        print("  --> Pipeline used raw OCR text as fallback")


def _print_sandbox_results(sandbox_data: dict | None) -> None:
    """Print sandbox compilation and execution results."""
    print(_sub_header("Stage 2: Sandbox (Compile & Execute)"))
    if sandbox_data is None:
        print("  No sandbox result found.")
        return

    comp = sandbox_data.get("compilation_result", {})
    print(f"  Compiled OK: {comp.get('success')}")
    if comp.get("errors"):
        print("  Compile Errors:")
        for err in comp["errors"]:
            print(f"    - {err}")

    exe = sandbox_data.get("execution_result", {})
    print(f"  Execution OK: {exe.get('success', 'N/A')}")
    if exe.get("errors"):
        print("  Runtime Errors:")
        for err in exe["errors"]:
            print(f"    - {err}")
    if exe.get("outputs"):
        print("  Outputs:")
        for i, out in enumerate(exe["outputs"], 1):
            print(f"    Case {i}: returncode={out.get('returncode')}")
            if out.get("stdout"):
                print(f"      stdout: {out['stdout']}")
            if out.get("stderr"):
                print(f"      stderr: {out['stderr']}")
            tc = out.get("test_case", {})
            if tc:
                print(
                    f"      input={tc.get('input')!r} expected={tc.get('expected_output')!r}"
                )

    tc_results = sandbox_data.get("test_cases_results", {})
    results = tc_results.get("results")
    if results:
        print("\n  Test Case Results:")
        for i, tc in enumerate(results, 1):
            status = "PASS" if tc.get("passed") else "FAIL"
            print(
                f"    Case {i}: [{status}] input={tc.get('input')!r} "
                f"expected={tc.get('expected_output')!r} actual={tc.get('actual_output')!r}"
            )


def _print_grader_results(grader_data: dict | None) -> None:
    """Print AI grader evaluation results."""
    print(_sub_header("Stage 3: AI Grader"))
    if grader_data is None:
        print("  No AI grader result found.")
        return

    rubric = grader_data.get("rubric_result_json", {})
    print(f"  Total Score:  {rubric.get('total_score')} / {rubric.get('max_score')}")
    print(f"  Final Grade:  {grader_data.get('final_grade')}")
    print(f"  Confidence:   {rubric.get('confidence')}")

    breakdown = rubric.get("rubric_breakdown", [])
    if breakdown:
        print("\n  Rubric Breakdown:")
        print(f"    {'Criterion':<20} {'Score':>10} {'Rationale'}")
        print(f"    {'-'*20} {'-'*10} {'-'*40}")
        for item in breakdown:
            name = item.get("criterion_id_or_name", "?")
            score = f"{item.get('earned_points')}/{item.get('max_points')}"
            rationale = item.get("rationale", "")
            print(f"    {name:<20} {score:>10} {rationale}")
            evidence = item.get("evidence_from_code_or_logs")
            if evidence:
                print(f"    {'':20} {'':>10} Evidence: {evidence}")

    feedback = rubric.get("feedback", {})
    if feedback:
        print(f"\n  Feedback Summary: {feedback.get('summary')}")
        issues = feedback.get("issues", [])
        if issues:
            print("  Issues:")
            for issue in issues:
                sev = issue.get("severity", "?")
                desc = issue.get("description", "?")
                loc = issue.get("location")
                loc_str = f" at {loc}" if loc else ""
                print(f"    - [{sev}]{loc_str} {desc}")
        suggestions = feedback.get("suggestions", [])
        if suggestions:
            print("  Suggestions:")
            for s in suggestions:
                print(f"    - {s}")
        next_steps = feedback.get("next_steps", [])
        if next_steps:
            print("  Next Steps:")
            for ns in next_steps:
                print(f"    - {ns}")

    err_class = rubric.get("error_classification", {})
    if err_class:
        print("\n  Error Classification:")
        print(
            f"    OCR/Handwriting suspected: {err_class.get('handwriting_ocr_suspected')}"
        )
        print(f"    Syntax/Compile error:      {err_class.get('syntax_or_compile')}")
        print(f"    Runtime error:             {err_class.get('runtime')}")
        print(f"    Logic error:               {err_class.get('logic')}")
        if err_class.get("notes"):
            print(f"    Notes: {err_class['notes']}")

    student_fb = grader_data.get("student_feedback")
    if student_fb:
        print(f"\n  Student Feedback: {student_fb}")
    instructor_g = grader_data.get("instructor_guidance")
    if instructor_g:
        print(f"  Instructor Guidance: {instructor_g}")


# ---------------------------------------------------------------------------
# Main pipeline runner
# ---------------------------------------------------------------------------


def run_pipeline(
    image_path: str,
    api_base: str,
    redis_url: str,
    timeout: int,
    restart_workers: bool = True,
) -> None:
    tag = uuid.uuid4().hex[:12]
    image_name = Path(image_path).name
    backend_dir = Path(__file__).resolve().parent.parent

    print(_header("E2E PIPELINE TEST"))
    print(f"  Image:     {image_path}")
    print(f"  API:       {api_base}")
    print(f"  Redis:     {redis_url}")
    print(f"  Timeout:   {timeout}s")
    print(f"  Run ID:    {tag}")

    worker_procs: list[subprocess.Popen] = []

    # ---- Step 0: (Re)start workers ----
    if restart_workers:
        print(_sub_header("Step 0: Restarting workers"))
        print("  Killing existing worker processes...")
        _kill_existing_workers()
        time.sleep(2)

        print("  Clearing stale Redis processing queue...")
        _clear_stale_redis_jobs(redis_url)

        print("  Starting API server and workers...")
        worker_procs = _start_workers(backend_dir)
        print("  Waiting up to 30s for API to become ready...")
        if not _wait_for_api(api_base, timeout=30):
            print(f"  ERROR: API did not start in time at {api_base}")
            _kill_workers(worker_procs)
            sys.exit(1)
        print(
            f"  API is ready. Waiting {WORKER_STARTUP_WAIT}s for workers to initialize..."
        )
        time.sleep(WORKER_STARTUP_WAIT)
        print("  Workers started.")
    else:
        print(_sub_header("Step 0: Checking API availability"))
        try:
            r = httpx.get(f"{api_base}/openapi.json", timeout=5.0)
            r.raise_for_status()
            print("  API is reachable.")
        except (httpx.HTTPError, OSError) as e:
            print(f"  ERROR: API not available at {api_base}: {e}")
            sys.exit(1)

    # ---- Step 1: Upload image to S3 ----
    print(_sub_header("Step 1: Uploading image to S3"))
    _upload_image_to_s3(image_path)

    # ---- Step 2: Register users, create course/assignment/question, enroll ----
    print(_sub_header("Step 2: Setting up test data"))
    with httpx.Client(base_url=api_base, timeout=60.0) as client:

        stu_user = f"e2e_pipe_stu_{tag}"
        inst_user = f"e2e_pipe_inst_{tag}"
        _register(
            client,
            username=stu_user,
            password="testpass123",
            email=f"{stu_user}@test.local",
            role="student",
        )
        _register(
            client,
            username=inst_user,
            password="testpass123",
            email=f"{inst_user}@test.local",
            role="instructor",
        )
        print(f"  Student:    {stu_user}")
        print(f"  Instructor: {inst_user}")

        stu_token = _login(client, username=stu_user, password="testpass123")
        inst_token = _login(client, username=inst_user, password="testpass123")
        inst_h = _auth(inst_token)
        stu_h = _auth(stu_token)

        r = client.post(
            "/courses/",
            params={
                "name": f"PipelineCourse {tag}",
                "description": "E2E pipeline test",
            },
            headers=inst_h,
        )
        r.raise_for_status()
        course_id = r.json()["id"]
        print(f"  Course:     id={course_id}")

        r = client.post(
            "/assignments/",
            params={
                "course_id": course_id,
                "title": f"PipelineHW {tag}",
                "description": "E2E",
            },
            json=RUBRIC,
            headers=inst_h,
        )
        r.raise_for_status()
        assignment_id = r.json()["id"]
        print(f"  Assignment: id={assignment_id}")

        r = client.post(
            f"/assignments/{assignment_id}/questions/",
            params={"question_text": QUESTION_TEXT},
            headers=inst_h,
        )
        r.raise_for_status()
        question_id = r.json()["id"]
        print(f"  Question:   id={question_id}")

        me = client.get("/users/me", headers=stu_h)
        me.raise_for_status()
        student_id = me.json()["id"]
        r = client.post(f"/courses/{course_id}/enroll/{student_id}", headers=inst_h)
        if r.status_code not in (200, 201, 409):
            r.raise_for_status()
        print(f"  Student {student_id} enrolled in course {course_id}")

        # ---- Step 3: Submit the image ----
        print(_sub_header("Step 3: Submitting image"))
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        submit_start = time.time()
        r = client.post(
            "/submissions/",
            data={"question_id": str(question_id), "assignment_id": str(assignment_id)},
            headers=stu_h,
            files={"file": (image_name, BytesIO(image_bytes), "image/png")},
        )
        r.raise_for_status()
        submission = r.json()
        submission_id = submission["id"]
        print(f"  Submission created: id={submission_id}")
        print(f"  Initial state:     {submission['state']}")

        # ---- Step 4: Poll for pipeline completion ----
        print(_sub_header("Step 4: Waiting for pipeline to complete"))
        start = time.time()
        final_state = submission["state"]
        while time.time() - start < timeout:
            time.sleep(POLL_INTERVAL)
            elapsed = time.time() - start
            r = client.get(f"/submissions/{submission_id}", headers=stu_h)
            r.raise_for_status()
            current = r.json()
            final_state = current["state"]
            print(f"  [{elapsed:5.1f}s] state = {final_state}")
            if final_state in ("graded", "failed"):
                break
        else:
            print(f"\n  TIMEOUT after {timeout}s. Last state: {final_state}")

        pipeline_duration = time.time() - submit_start

        # ---- Step 5: Fetch full job result from Redis ----
        print(_header("PIPELINE RESULTS"))
        print(f"  Submission ID:     {submission_id}")
        print(f"  Final State:       {final_state}")
        print(f"  Pipeline Duration: {pipeline_duration:.1f}s")

        job_result = _find_job_result(redis_url, submission_id)
        if job_result:
            print(f"  Job ID:            {job_result.get('job_id')}")
            print(f"  Job Status:        {job_result.get('status')}")

            ocr_result, llm_result = _extract_ocr_data(job_result)
            sandbox_data = _extract_sandbox_data(job_result)
            grader_data = _extract_grader_data(job_result)

            _print_ocr_results(ocr_result, llm_result)
            _print_sandbox_results(sandbox_data)
            _print_grader_results(grader_data)
        else:
            print("  WARNING: Job result not found in Redis completed queue.")
            print("  Falling back to API-only results...\n")

            # Fallback: fetch from API endpoints
            print(_sub_header("OCR Transcription (API)"))
            r = client.get(f"/grading/{submission_id}/transcription", headers=stu_h)
            if r.status_code == 200:
                transcription = r.json()
                print("  Transcribed Text (best available — raw OCR or LLM corrected):")
                text = transcription.get("transcribed_text") or "(empty)"
                for line in text.split("\n"):
                    print(f"    | {line}")
            else:
                print("  No transcription found.")

            print(_sub_header("Sandbox Compile Result (API)"))
            r = client.get(f"/grading/{submission_id}/compile_result", headers=stu_h)
            if r.status_code == 200:
                cr = r.json()
                print(f"  Compiled OK: {cr['compiled_ok']}")
                if cr.get("compile_errors"):
                    print(f"  Errors: {cr['compile_errors']}")
            else:
                print("  No compile result found.")

            print(_sub_header("AI Grader Feedback (API)"))
            r = client.get(f"/grading/{submission_id}/ai_feedback", headers=stu_h)
            if r.status_code == 200:
                fb = r.json()
                print(f"  Suggested Grade:     {fb.get('suggested_grade')}")
                print(f"  Student Feedback:    {fb.get('student_feedback')}")
                print(f"  Instructor Guidance: {fb.get('instructor_guidance')}")
            else:
                print("  No AI feedback found.")

        # ---- Summary ----
        print(_header("SUMMARY"))
        passed = final_state == "graded"
        print(f"  Image:               {image_name}")
        print(f"  Submission ID:       {submission_id}")
        print(f"  Final State:         {final_state}")
        print(f"  Pipeline Duration:   {pipeline_duration:.1f}s")

        ai_check = client.get(f"/grading/{submission_id}/ai_feedback", headers=stu_h)
        if ai_check.status_code == 200:
            fb = ai_check.json()
            print(f"  Suggested Grade:     {fb.get('suggested_grade')}")
            print("  AI Grader Evaluated: YES")
        else:
            print("  AI Grader Evaluated: NO")

        if job_result:
            ocr_result, llm_result = _extract_ocr_data(job_result)
            ocr_ok = ocr_result.get("success") if ocr_result else False
            llm_ok = llm_result.get("success") if llm_result else False
            print(f"  OCR Extraction:      {'OK' if ocr_ok else 'FAILED'}")
            print(f"  LLM Correction:      {'OK' if llm_ok else 'FAILED'}")

        result_str = "PASS" if passed else "FAIL"
        print(f"  Pipeline Result:     {result_str}")

    # ---- Cleanup: stop workers we started ----
    if worker_procs:
        print(_sub_header("Cleanup: stopping workers"))
        _kill_workers(worker_procs)
        print("  Workers stopped.")

    if not passed:
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Run E2E pipeline test with a specific image."
    )
    parser.add_argument("image_path", help="Path to the image file to test with")
    parser.add_argument(
        "--api-base",
        default=os.environ.get("E2E_API_BASE", DEFAULT_API_BASE),
        help=f"API base URL (default: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--redis-url",
        default=os.environ.get("REDIS_ENDPOINT", DEFAULT_REDIS_URL),
        help=f"Redis URL (default: {DEFAULT_REDIS_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Max seconds to wait for pipeline (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--no-restart-workers",
        action="store_true",
        default=False,
        help="Skip killing and restarting workers (use if workers are already running)",
    )
    args = parser.parse_args()

    image = Path(args.image_path)
    if not image.exists():
        print(f"ERROR: Image not found: {image}")
        sys.exit(1)

    run_pipeline(
        str(image),
        args.api_base,
        args.redis_url,
        args.timeout,
        restart_workers=not args.no_restart_workers,
    )


if __name__ == "__main__":
    main()
