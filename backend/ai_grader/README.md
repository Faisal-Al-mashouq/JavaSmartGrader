# AI Grader Worker

Standalone AI grading worker for JavaSmartGrader. All implementation is isolated under `ai_grader/` and can run without modifying existing repo files.

## Behavior Implemented

Worker loop follows the required flow:

1. `job = QueueAdapter.dequeue("Ready_Grading")`
2. `code = DatabaseAdapter.get_transcription(submission_id)`
3. `logs = DatabaseAdapter.get_sandbox_results(submission_id)`
4. `rubric = DatabaseAdapter.get_rubric(submission_id)`
5. `prompt = construct_prompt(...)`
6. `response = LLMClient.call(model, prompt)` with retries/backoff+jitter
7. `parsed = parse_and_validate_json(response.text)`
8. `DatabaseAdapter.save_feedback(submission_id, parsed)` (`ai_feedback`)
9. `DatabaseAdapter.update_status(submission_id, "Pending_Review")`
10. Retryable API errors (timeouts/429/5xx/network) are retried exponentially with jitter.

If output JSON is invalid:

- Exactly one repair call is made with `construct_repair_prompt(...)`.
- If still invalid, a failure feedback record is persisted when possible.
- Failure status update is attempted only if a compatible state exists; otherwise status is left unchanged.

## Required Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODEL` | No | `ft:gpt-4.1-mini` | Fine-tuned (or regular) model id used by LLM API |
| `API_KEY` | Yes | `""` | LLM API key |
| `BASE_URL` | No | `https://api.openai.com/v1` | LLM base URL (OpenAI-compatible chat completions endpoint) |
| `TIMEOUT_S` | No | `30` | HTTP timeout in seconds |
| `MAX_RETRIES` | No | `3` | Number of retries for retryable API failures |
| `BACKOFF_BASE_S` | No | `1.0` | Initial exponential backoff delay |
| `BACKOFF_MAX_S` | No | `30.0` | Max backoff delay |
| `REDIS_ENDPOINT` | No | uses `REDIS_URL` or `redis://localhost:6379` | Redis URL for queue |
| `READY_GRADING_QUEUE` | No | `Ready_Grading` | Queue name consumed by this worker |
| `QUEUE_POLL_TIMEOUT_S` | No | `5` | BRPOP timeout |
| `PENDING_REVIEW_STATUS` | No | `Pending_Review` | Success status value to apply |
| `FAILURE_STATUS_CANDIDATES` | No | `Grading_Failed,failed` | Comma-separated failure states to try in order |
| `BACKEND_PATH` | No | `<repo>/backend` | Path added to import existing `db.*` modules |

## How to Run Locally

From repo root:

```bash
python -m ai_grader.main
```

Single-job mode:

```bash
python -m ai_grader.main --once
```

Self-test script:

```bash
python -m ai_grader.self_test
```

## Integration Notes

### Queue Adapter

- File: `ai_grader/adapters/queue_adapter.py`
- Uses Redis list queue via `BRPOP`.
- Expected payload forms:
  - integer string: `"123"`
  - JSON object: `{"submission_id": 123}`
  - JSON object: `{"id": 123}`
  - JSON object: `{"submission": {"id": 123}}`

### Database Adapter

- File: `ai_grader/adapters/database_adapter.py`
- Attempts to import existing backend modules:
  - `db.session.async_session`
  - `db.models.Submission`, `db.models.AIFeedback`, `db.models.SubmissionState`
- Maps data sources to current schema:
  - `Get_Transcription` -> `submissions.transcription.transcribed_text`
  - `Get_Sandbox_Results` -> `submissions.compile_results` fields (`compiled_ok`, `compile_errors`, `runtime_errors`, `runtime_output`)
  - `Get_Rubric` -> `submissions.assignment.rubric_json`
  - `Save_Feedback` -> upsert `ai_feedback` (`suggested_grade = total_score`, `feedback_text = full JSON`)
  - `Update_Status` -> updates `submissions.state` only if target status exists in enum

If backend imports are not discoverable in another repo layout, the adapter falls back to a placeholder with clear runtime errors. Map methods in `PlaceholderDatabaseAdapter` to your infrastructure.

## Example Expected AI JSON Output

```json
{
  "submission_id": 123,
  "total_score": 17.5,
  "max_score": 20,
  "rubric_breakdown": [
    {
      "criterion_id_or_name": "Compilation",
      "earned_points": 5,
      "max_points": 5,
      "rationale": "Code compiles successfully.",
      "evidence_from_code_or_logs": "compiled_ok: true"
    },
    {
      "criterion_id_or_name": "Correctness",
      "earned_points": 8.5,
      "max_points": 10,
      "rationale": "Most expected outputs match; one edge case fails.",
      "evidence_from_code_or_logs": "runtime_output mismatch on input=0"
    },
    {
      "criterion_id_or_name": "Style",
      "earned_points": 4,
      "max_points": 5,
      "rationale": "Readable but missing comments in key method.",
      "evidence_from_code_or_logs": "Method parseInput lacks inline explanation."
    }
  ],
  "feedback": {
    "summary": "Strong submission with one edge-case bug and minor style issues.",
    "issues": [
      {
        "location": "Line 27",
        "description": "Division by zero not handled for input=0.",
        "severity": "high"
      }
    ],
    "suggestions": [
      "Add guard clauses for zero and null inputs.",
      "Include comments for non-obvious logic."
    ],
    "next_steps": [
      "Re-run tests including boundary inputs.",
      "Refactor error handling into helper methods."
    ]
  },
  "error_classification": {
    "handwriting_ocr_suspected": false,
    "syntax_or_compile": false,
    "runtime": true,
    "logic": true,
    "notes": "Runtime mismatch on edge case indicates logic branch gap."
  },
  "confidence": 0.84
}
```
