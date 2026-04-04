# API Layer

FastAPI route layer for JavaSmartGrader.

## Run

From `backend/`:

```bash
uv run task dev    # APP_ENV=dev — common for local MinIO / custom S3 endpoint
# or
uv run task local  # APP_ENV=local — typical AWS S3 without custom endpoint
```

Open interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## Core Modules

| File | Responsibility |
|------|----------------|
| `auth.py` | JWT creation/verification and role guards |
| `dependencies.py` | Shared dependencies (DB session, auth helpers) |
| `s3.py` | Upload submissions to S3-compatible storage; helpers for keys and public-style URLs |
| `routes/users.py` | Registration, login, user profile endpoints |
| `routes/courses.py` | Course CRUD and enrollment flows |
| `routes/assignments.py` | Assignment CRUD |
| `routes/questions.py` | Question + testcase endpoints under assignments |
| `routes/submissions.py` | Submission creation (multipart: `question_id`, `assignment_id`, `file`) and retrieval |
| `routes/grading.py` | Compile/OCR/AI feedback + final grade endpoints |
| `routes/confidence_flags.py` | OCR confidence flag endpoints |
| `routes/generate_report.py` | Assignment report endpoints |

## Router Prefixes

- `/users`
- `/courses`
- `/assignments`
- `/assignments/{assignment_id}/questions`
- `/submissions`
- `/grading`
- `/confidence-flags`
- `/reports`

## Authentication

- Auth uses Bearer JWTs (`HS256`) from `POST /users/login`.
- Default token expiry: **30 minutes**.
- Role gates are enforced in route dependencies (`student` vs `instructor`).

Header format:

```text
Authorization: Bearer <token>
```

## Notes

- The OpenAPI spec in `/docs` is the source of truth for request/response schemas.
- `POST /submissions/` expects **multipart/form-data**: form fields `question_id` and `assignment_id` (ints as strings) plus a required file part `file`. The API uploads to the configured bucket and persists the **object key** (e.g. `submissions/{submission_id}/{filename}`) in `Submission.image_url`.
- Lifespan startup in `backend/main.py` starts the queue orchestrator (`core/job_queue.py`) and, for supported environments, sandbox, OCR, and AI grader worker tasks so submission flows can reach downstream workers.

## Tests

- Route and auth unit tests: `api/test.py` (run from `backend/` with `uv run pytest api/test.py`, or use the full suite: `uv run pytest`).
- Full HTTP flow (register → course → assignment → question → enroll → submit): `tests/test_submission.py`, marked `e2e` (requires running API, DB, and S3; see `backend/README.md`).
