# AI Grader Worker

The AI Grader is a standalone worker that consumes grading jobs from Redis, calls an OpenAI-compatible LLM endpoint, validates the JSON response, and writes feedback + status updates back to the database. It is designed to operate safely during OCR rollout by preferring payload inputs and falling back to the DB when needed.

## Pipeline Integration (Recent Changes)

- Wired the AI grader into the main job pipeline using the same queue pattern as the sandbox (push to queue, wait on `:completed:{job_id}`).
- Implemented `process_grader_job` to enqueue `GraderPayload`, await completion, and store `GraderResult` on the job.
- Added `submission_id` to `GraderPayload` so queue messages are self-contained.
- Enhanced the AI grader worker to parse payload inputs (transcribed text, sandbox results, rubric) and build logs directly from sandbox output.
- Added payload-first behavior with DB fallback for robustness during OCR rollout.
- Added job completion publishing from the AI grader worker to `Ready_Grading:completed:{job_id}`.
- Updated queue adapter to extract `job_id` and support pushing completion payloads.
- Normalized queue naming to respect namespace prefixes across core + `ai_grader`.
- Added a single-repair pass for invalid LLM JSON output to improve resilience.
- Persisted failure feedback and attempted failure status updates when grading cannot be recovered.
- Standardized completion payloads to include `final_grade` and `student_feedback` when available.

## Unit Tests (General Coverage)

The AI grader unit tests focus on core behavior across modules, with external services mocked or stubbed:

- **LLM client**: URL normalization, retries/backoff paths, error classification, payload shape, and content extraction.
- **Parser/validator**: JSON schema validation, submission_id matching, and failure handling.
- **Prompt builder**: Verbatim inclusion of rubric/code/logs and schema presence.
- **Orchestration**: single-repair flow, success and failure branches, completion payloads, and log formatting.
- **Queue adapter**: extraction of `submission_id`/`job_id` from multiple payload formats.
- **Database adapter**: placeholder behavior and fallback adapter creation.

Run tests locally:

```bash
pytest backend/ai_grader/self_test.py
```

## Worker Flow

1. Dequeue a job from `Ready_Grading` (namespace-aware).
2. Build inputs:
   - Prefer payload fields (`transcribed_text`, `sandbox_result`, `rubric_json`).
   - Fallback to DB (`get_transcription`, `get_sandbox_results`, `get_rubric`).
3. Construct the grading prompt with schema and rubric.
4. Call the LLM with retries/backoff + jitter for retryable failures.
5. Parse and validate JSON; if invalid, perform a single repair call.
6. On success: save feedback + update status to `Pending_Review`.
7. On failure: persist failure feedback and attempt failure status update.
8. Publish completion to `Ready_Grading:completed:{job_id}`.

## Queue Payloads

### Grader Payload (Input)

Queue message is JSON and includes `submission_id` (self-contained), plus optional payload data to avoid DB dependency during OCR rollout.

Example:

```json
{
  "job_id": "job-123",
  "submission_id": 123,
  "transcribed_text": "class Main { ... }",
  "sandbox_result": {
    "result": {
      "compilation_result": { "success": true, "errors": "" },
      "execution_result": { "errors": "", "outputs": [] },
      "test_cases_results": { "results": [] }
    }
  },
  "rubric_json": { "criteria": [{ "name": "Correctness", "points": 10 }] }
}
```

### Completion Payload (Output)

Published to `Ready_Grading:completed:{job_id}`.

Example success:

```json
{
  "job_id": "job-123",
  "submission_id": 123,
  "status": "COMPLETED",
  "rubric_result_json": { "total_score": 9, "feedback": { "summary": "Nice job." } },
  "final_grade": 9.0,
  "student_feedback": "Nice job."
}
```

Example failure:

```json
{
  "job_id": "job-123",
  "submission_id": 123,
  "status": "FAILED",
  "error": "LLM call failed after 2 attempts",
  "raw_output": "{ ... }"
}
```

## Queue Naming and Namespaces

- `READY_GRADING_QUEUE` defaults to `Ready_Grading`.
- If `QUEUE_NAMESPACE` is set (e.g., `jsg.v1`), the worker ensures queues are prefixed, e.g. `jsg.v1:Ready_Grading`.
- Completion queues are always `:completed:{job_id}` off the same base queue.

## Required Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODEL` | No | `ft:gpt-4.1-nano-` | Model id used by the LLM API |
| `API_KEY` | Yes | `""` | LLM API key |
| `BASE_URL` | No | `https://api.openai.com/v1` | OpenAI-compatible base URL |
| `TIMEOUT_S` | No | `30` | HTTP timeout in seconds |
| `MAX_RETRIES` | No | `3` | Retry count for retryable failures |
| `BACKOFF_BASE_S` | No | `1.0` | Exponential backoff base |
| `BACKOFF_MAX_S` | No | `30.0` | Exponential backoff cap |
| `REDIS_ENDPOINT` | No | uses `REDIS_URL` or `redis://localhost:6379` | Redis URL |
| `READY_GRADING_QUEUE` | No | `Ready_Grading` | Base queue name |
| `QUEUE_POLL_TIMEOUT_S` | No | `5` | BRPOP timeout |
| `PENDING_REVIEW_STATUS` | No | `Pending_Review` | Status applied on success |
| `FAILURE_STATUS_CANDIDATES` | No | `Grading_Failed,failed` | Ordered failure statuses to attempt |
| `BACKEND_PATH` | No | `<repo>/backend` | Added to `sys.path` for DB imports |

## How to Run Locally

From repo root:

```bash
python -m ai_grader.main
```

On startup, `main` loads settings, initializes the Redis queue adapter, database
adapter, and LLM client, then enters the worker loop. The worker waits on the
queue, processes jobs using the payload-first flow, publishes completion payloads,
and keeps running until interrupted.

Single-job mode:

```bash
python -m ai_grader.main --once
```

## Tests

Run the unit test suite:

```bash
pytest backend/ai_grader/self_test.py
```

## Integration Notes

### Queue Adapter

- File: `ai_grader/adapters/queue_adapter.py`
- Uses Redis list queue via `BRPOP`.
- Extracts `submission_id` from several payload formats and supports `job_id`.

### Database Adapter

- File: `ai_grader/adapters/database_adapter.py`
- Attempts to import existing backend modules:
  - `db.session.async_session`
  - `db.models.Submission`, `db.models.AIFeedback`, `db.models.SubmissionState`
- Maps data sources to current schema:
  - `get_transcription` -> `submissions.transcription.transcribed_text`
  - `get_sandbox_results` -> `submissions.compile_results` fields
  - `get_rubric` -> `submissions.assignment.rubric_json`
  - `save_feedback` -> upsert `ai_feedback` (`suggested_grade = total_score`)
  - `update_status` -> updates `submissions.state` only if target status exists in enum

If backend imports are not discoverable in another repo layout, the adapter falls back to a placeholder with clear runtime errors. Map methods in `PlaceholderDatabaseAdapter` to your infrastructure.
