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
# FastAPI with APP_ENV=dev (MinIO-friendly S3 client: custom endpoint)
uv run task dev

# FastAPI with APP_ENV=local (typical AWS-style S3 client without custom endpoint)
uv run task local

# FastAPI with APP_ENV=all (starts API + job queue + sandbox + OCR + AI grader workers)
uv run task all
```

`APP_ENV` is one of `local`, `dev`, `prod`, or `all` (`backend/settings.py`). Sandbox, OCR, and AI grader workers are started as asyncio tasks during API lifespan today; `main.py` still carries TODOs for splitting workers out in production.

API base URL: [http://localhost:8000](http://localhost:8000)  
Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Settings

Create `backend/.env` (loaded by `pydantic-settings`):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
REDIS_ENDPOINT=redis://localhost:6379
QUEUE_NAMESPACE=jsg.v1
AI_GRADING_QUEUE=AIGradingJobQueue
JWT_SECRET_KEY=change-me
MAX_CONCURRENCY=10

# Submission storage (see .env.example for full list)
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=submissions-local
S3_REGION=us-east-1
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
└── pyproject.toml     # Dependencies and task commands
```

## Helpful Commands

```bash
# Lint + format (black + ruff from repository root)
uv run task lint

# Run sandbox worker only
uv run task sandbox

# Run OCR worker only
uv run task ocr

# Run AI grader worker only
uv run task ai_grader
```

## Component Docs

- API: `api/README.md`
- Database: `db/README.md`
- Sandbox worker: `sandbox/README.md`
- AI grader worker: `ai_grader/README.md`
- OCR pipeline: `ocr/README.md`
