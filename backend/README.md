# JavaSmartGrader Backend

Python 3.12 FastAPI backend for JavaSmartGrader, including:

- REST API routes and authentication
- async SQLAlchemy/PostgreSQL data layer
- Redis-backed job orchestration (`core/job_queue.py`)
- Docker-isolated Java sandbox execution
- OCR correction worker integration
- AI grader queue worker integration

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL
- Redis
- Docker

## Install

```bash
cd backend
uv sync
```

## Run Modes

From `backend/`:

```bash
# FastAPI with APP_ENV=dev
uv run task dev

# FastAPI with APP_ENV=local
uv run task local

# FastAPI with APP_ENV=all (starts API + job queue + sandbox + OCR workers)
uv run task all
```

API base URL: [http://localhost:8000](http://localhost:8000)  
Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Settings

Create `backend/.env` (loaded by `pydantic-settings`):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
REDIS_ENDPOINT=redis://localhost:6379
QUEUE_NAMESPACE=jsg.v1
JWT_SECRET_KEY=change-me
MAX_CONCURRENCY=10
```

See `settings.py` for the full list of configurable values.

## Project Layout

```text
backend/
├── main.py            # FastAPI app + lifespan startup/shutdown orchestration
├── api/               # Auth, dependencies, and route handlers
├── core/              # Job queue orchestrator and processing pipeline
├── db/                # SQLAlchemy models, CRUD, session, Alembic migrations
├── sandbox/           # Docker sandbox worker (compile/execute Java submissions)
├── ocr/               # OCR correction pipeline and worker
├── schemas/           # Shared Pydantic schemas
└── pyproject.toml     # Dependencies and task commands
```

## Helpful Commands

```bash
# Lint + format
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
- OCR pipeline: `ocr/README.md`
