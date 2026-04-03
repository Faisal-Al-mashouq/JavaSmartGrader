# AI Grader Worker

The AI Grader is a standalone queue worker that consumes grading jobs from Redis, calls an OpenAI-compatible LLM endpoint, validates the JSON response, and publishes a completion payload back to Redis. It does not write to the database; the API / job runner applies `GraderResult` after reading `:completed:{job_id}`.

## Pipeline Integration (Recent Changes)

- Wired the AI grader into the main job pipeline using the same queue pattern as the sandbox (push to queue, wait on `:completed:{job_id}`).
- Implemented `process_grader_job` to enqueue `GraderPayload`, await completion, and store `GraderResult` on the job.
- Added `submission_id` to `GraderPayload` so queue messages are self-contained.
- Enhanced the AI grader worker to parse payload inputs (transcribed text, sandbox results, rubric) and build logs directly from sandbox output.
- Removed runtime DB adapter dependency; worker now uses queue payload only.
- Added job completion publishing from the AI grader worker to `{namespace}:AIGradingJobQueue:completed:{job_id}` (see **Queue naming** below).
- Updated queue adapter to extract `job_id` and support pushing completion payloads (used elsewhere; the worker loop uses Redis directly).
- Namespace rules for the AI grading queue match `core.process.grader` (`AI_GRADER_QUEUE`).
- Added a single-repair pass for invalid LLM JSON output to improve resilience.
- Standardized completion payloads to include `final_grade` and `student_feedback` when available.

## Unit Tests (General Coverage)

The AI grader unit tests focus on core behavior across modules, with external services mocked or stubbed:

- **LLM client**: URL normalization, retries/backoff paths, error classification, payload shape, and content extraction.
- **Parser/validator**: JSON schema validation, submission_id matching, and failure handling.
- **Prompt builder**: Verbatim inclusion of rubric/code/logs and schema presence.
- **Orchestration**: single-repair flow, success and failure branches, completion payloads, log formatting, and `main_loop` / `run_worker` wiring.
- **Queue adapter**: extraction of `submission_id`/`job_id` from multiple payload formats.

Run tests locally:

```bash
pytest backend/ai_grader/self_test.py
```

## Worker Flow

1. Resolve the work queue name with the same prefix rule as the job runner (see **Queue naming**).
2. Dequeue via `BRPOPLPUSH` into `{queue}:processing`.
3. Parse the JSON job (`job_id`, `submission_id`, `transcribed_text`, `sandbox_result`, `rubric_json`).
4. Build the grading prompt (schema + rubric + sandbox logs).
5. Call the LLM with retries/backoff + jitter for retryable failures.
6. Parse and validate JSON; if invalid, perform a single repair call.
7. `LPUSH` the completion payload to `{queue}:completed:{job_id}`.
8. `LREM` the raw message from `{queue}:processing` when publish succeeds.

## Queue Payloads

### Grader Payload (Input)

Queue message is JSON and includes `submission_id` and `job_id`, plus grading inputs.

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

Published to `{resolved_queue}:completed:{job_id}`.

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

- `AI_GRADING_QUEUE` defaults to `AIGradingJobQueue` (see `backend/.env.example`).
- If `QUEUE_NAMESPACE` is set (e.g. `jsg.v1`), the effective queue is `jsg.v1:AIGradingJobQueue` unless you already prefixed `AI_GRADING_QUEUE` with that namespace (same logic as `AI_GRADER_QUEUE` in `core.process.grader`).
- Processing list: `{resolved_queue}:processing`.
- Completion list: `{resolved_queue}:completed:{job_id}`.

## Required Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODEL` | No | `ft:gpt-4.1-nano-` | Model id used by the LLM API (`OPENAI_MODEL` also accepted) |
| `API_KEY` | Yes | `""` | LLM API key (`OPENAI_API_KEY` also accepted) |
| `BASE_URL` | No | `https://api.openai.com/v1` | OpenAI-compatible base URL |
| `TIMEOUT_S` | No | `30` | HTTP timeout in seconds |
| `MAX_RETRIES` | No | `3` | Retry count for retryable failures |
| `BACKOFF_BASE_S` | No | `1.0` | Exponential backoff base |
| `BACKOFF_MAX_S` | No | `30.0` | Exponential backoff cap |
| `LLM_TEMPERATURE` | No | `0.0` | LLM sampling temperature |
| `REDIS_ENDPOINT` | No | uses `REDIS_URL` or `redis://redis:6379` | Preferred Redis URL |
| `REDIS_URL` | No | `redis://redis:6379` | Fallback Redis URL when `REDIS_ENDPOINT` is unset |
| `QUEUE_NAMESPACE` | No | `jsg.v1` | Prefix for queue names when the base name is not already prefixed |
| `AI_GRADING_QUEUE` | No | `AIGradingJobQueue` | Base AI grading queue name |
| `QUEUE_POLL_TIMEOUT_S` | No | `0` | `BRPOPLPUSH` timeout (seconds) |
| `PENDING_REVIEW_STATUS` | No | `Pending_Review` | Used only if worker code references status helpers |
| `FAILURE_STATUS_CANDIDATES` | No | `Grading_Failed,failed` | Same as above |
| `BACKEND_PATH` | No | computed from runtime path | Reserved for auxiliary imports |
| `LOG_LEVEL` | No | `INFO` | Root log level for the ai_grader worker |

Notes:

- Redis URL resolution priority is `REDIS_ENDPOINT` -> `REDIS_URL` -> default.

## How to Run Locally

From `backend/`:

```bash
uv run task ai_grader
```

Or:

```bash
uv run python -m ai_grader.main
```

On startup, `main` loads settings, opens a Redis client, constructs the LLM client, and runs `main_loop` until interrupted.

Single-job mode:

```bash
python -m ai_grader.main --once
```

## Tests

```bash
pytest backend/ai_grader/self_test.py
```

## Integration Notes

The queue worker methodology now mirrors sandbox worker design:
- claim via `BRPOPLPUSH` into `:processing`
- process one typed payload
- publish to `:completed:{job_id}`
- remove from `:processing` with `LREM`

- File: `ai_grader/adapters/queue_adapter.py`
- Uses Redis list queue via `BRPOPLPUSH` for atomic claim into `:processing`.
- Extracts `submission_id` from several payload formats and supports `job_id`.

### Database

Persistence of grades and submission state is owned by the main backend after it consumes the Redis completion message, not by this worker process.
