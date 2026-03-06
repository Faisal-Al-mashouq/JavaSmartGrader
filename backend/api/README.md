# API Layer

FastAPI route layer for JavaSmartGrader.

## Run

From `backend/`:

```bash
uv run task local
```

Open interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## Core Modules

| File | Responsibility |
|------|----------------|
| `auth.py` | JWT creation/verification and role guards |
| `dependencies.py` | Shared dependencies (DB session, auth helpers) |
| `routes/users.py` | Registration, login, user profile endpoints |
| `routes/courses.py` | Course CRUD and enrollment flows |
| `routes/assignments.py` | Assignment CRUD |
| `routes/questions.py` | Question + testcase endpoints under assignments |
| `routes/submissions.py` | Submission creation and retrieval |
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
- Lifespan startup in `backend/main.py` also starts the queue orchestrator (`core/job_queue.py`), so submission flows can trigger downstream workers.
