# AI Grader Worker

The AI Grader is a standalone queue worker that consumes grading jobs from Redis, calls an OpenAI-compatible LLM endpoint, validates the JSON response, and publishes a completion payload back to Redis. It is stateless at runtime and does not write to the database directly.

## Pipeline Integration (Recent Changes)

- Wired the AI grader into the main job pipeline using the same queue pattern as the sandbox (push to queue, wait on `:completed:{job_id}`).
- Implemented `process_grader_job` to enqueue `GraderPayload`, await completion, and store `GraderResult` on the job.
- Added `submission_id` to `GraderPayload` so queue messages are self-contained.
- Enhanced the AI grader worker to parse payload inputs (transcribed text, sandbox results, rubric) and build logs directly from sandbox output.
- Removed runtime DB adapter dependency; worker now uses queue payload only.
- Added job completion publishing from the AI grader worker to `Ready_Grading:completed:{job_id}`.
- Updated queue adapter to extract `job_id` and support pushing completion payloads.
- Normalized queue naming to respect namespace prefixes across core + `ai_grader`.
- Added a single-repair pass for invalid LLM JSON output to improve resilience.
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
   - Claim is atomic via `BRPOPLPUSH` into `Ready_Grading:processing`.
2. Build inputs from queue payload fields (`transcribed_text`, `sandbox_result`, `rubric_json`).
3. Construct the grading prompt with schema and rubric.
4. Call the LLM with retries/backoff + jitter for retryable failures.
5. Parse and validate JSON; if invalid, perform a single repair call.
6. Publish completion to `Ready_Grading:completed:{job_id}`.
7. Remove the handled job from `Ready_Grading:processing` via `LREM`.

Database persistence (AI feedback + submission status) is handled upstream by `core/process/grader.py` after consuming completion payloads.

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
| `QUEUE_NAMESPACE` | No | `jsg.v1` | Prefix used for queue names (e.g. `jsg.v1:Ready_Grading`) |
| `READY_GRADING_QUEUE` | No | `Ready_Grading` | Base queue name |
| `QUEUE_POLL_TIMEOUT_S` | No | `5` | BRPOPLPUSH timeout |
| `LOG_LEVEL` | No | `INFO` | Root log level for the ai_grader worker |

Notes:

- Redis URL resolution priority is `REDIS_ENDPOINT` -> `REDIS_URL` -> default.
- Legacy aliases are mapped automatically:
  - `Pending_Review` -> `graded`
  - `Grading_Failed` -> `failed`
- In this repo layout, set `BACKEND_PATH` explicitly to your backend module root (usually `.../JavaSmartGrader/backend`) if dynamic DB imports fail.

## How to Run Locally

From repo root:

```bash
python -m ai_grader.main
```

On startup, `main` loads settings, initializes the Redis client and LLM client,
then enters the worker loop. The worker waits on the queue, processes jobs from
payload data, publishes completion payloads, and keeps running until interrupted.

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

The queue worker methodology now mirrors sandbox worker design:
- claim via `BRPOPLPUSH` into `:processing`
- process one typed payload
- publish to `:completed:{job_id}`
- remove from `:processing` with `LREM`

Database writes are intentionally outside this worker and performed by the core pipeline consumer.
