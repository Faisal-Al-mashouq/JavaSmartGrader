# JavaSmartGrader Backend

Python 3.12 FastAPI backend for JavaSmartGrader, including:

- REST API routes and authentication
- async SQLAlchemy/PostgreSQL data layer
- Redis-backed job orchestration (`core/job_queue.py`)
- Docker-isolated Java sandbox execution
- OCR correction worker integration
- AI grader queue worker integration
- S3-compatible object storage for submission images (API upload + OCR fetch)

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL
- Redis
- Docker
- S3-compatible storage (configure `S3_*` in `.env`; use `S3_ENDPOINT_URL` for MinIO in dev)

## Install

```bash
cd backend
uv sync
```

## Run Modes

From `backend/`:

```bash
# FastAPI with APP_ENV=dev (MinIO-friendly S3 client: custom endpoint), LOG_LEVEL=DEBUG
uv run task dev

# FastAPI with APP_ENV=local (typical AWS-style S3 client without custom endpoint)
uv run task local

# FastAPI with APP_ENV=prod
uv run task prod
```

`APP_ENV` is one of `local`, `dev`, or `prod` (`backend/settings.py`). Sandbox, OCR, and AI grader workers are started as asyncio tasks during API lifespan in supported environments; `main.py` still carries TODOs for splitting workers out in production.

API base URL: [http://localhost:8000](http://localhost:8000)  
Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Settings

Create `backend/.env` (loaded by `pydantic-settings`):

```env
env.example
```

See `settings.py` and `.env.example` for the full list of configurable values.

## Project Layout

```text
backend/
├── main.py            # FastAPI app + lifespan startup/shutdown orchestration
├── api/               # Auth, dependencies, route handlers, S3 upload helpers
├── core/              # Job queue orchestrator and processing pipeline
├── db/                # SQLAlchemy models, CRUD, session, Alembic migrations
├── sandbox/           # Docker sandbox worker (compile/execute Java submissions)
├── ocr/               # OCR correction pipeline and worker
├── ai_grader/         # LLM grader Redis worker
├── schemas/           # Shared Pydantic schemas
├── tests/             # Cross-cutting tests (e.g. HTTP e2e submission flow)
└── pyproject.toml     # Dependencies, pytest options, and task commands
```

## Tests

From `backend/`:

```bash
# All discovered tests (per-package test.py, tests/test_*.py, etc.)
uv run pytest

# Exclude live HTTP e2e (tests/test_submission.py)
uv run pytest -m "not e2e"

# Only e2e (API must be up; DB + S3 as for normal dev)
uv run pytest -m e2e
```

Pytest is configured in `pyproject.toml`: `pythonpath` includes `.`, `test.py` is an explicit test file pattern (alongside `test_*.py`), and `--import-mode=importlib` avoids import clashes when many packages define `test.py`. Optional: `E2E_API_BASE` overrides the default `http://localhost:8000` for e2e tests.

Other commands:

```bash
# Lint + format (black + ruff from repository root)
uv run task lint
```

Run workers standalone (when not using the API lifespan) if needed:

```bash
uv run python -m sandbox.sandbox_worker
uv run python -m ocr.main
uv run python -m ai_grader.main
```

## Component Docs

- API: `api/README.md`
- Database: `db/README.md`
- Sandbox worker: `sandbox/README.md`
- AI grader worker: `ai_grader/README.md`
- OCR pipeline: `ocr/README.md`
