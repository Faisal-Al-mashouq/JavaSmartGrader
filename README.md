# JavaSmartGrader

JavaSmartGrader is an automated grading platform for handwritten Java submissions.  
It combines a FastAPI backend, async Redis workers, Docker-based Java sandboxing, OCR correction, and a React frontend.

## Repository Layout

```text
JavaSmartGrader/
├── backend/          # FastAPI API, DB layer, queue orchestration, workers
├── frontend/         # React app
├── docker-compose.yml
└── README.md         # This file — component docs live under backend/*/README.md
```

## Environment setup

Copy the example env files once, then fill in secrets and paths. Run these from the **repository root**:

```bash
# Compose variable substitution (sandbox bind-mount path)
cp .env.example .env

# Backend API + workers
cp backend/.env.example backend/.env
```

| File | Purpose |
|------|---------|
| `.env` | Read by `docker compose` — currently `SANDBOX_HOST_TMP_PATH` only |
| `backend/.env` | API and workers (`pydantic-settings`); see `backend/settings.py` |
| `backend/.env.local` | Optional overlay when `APP_ENV=local` (not used inside Compose images by default) |

**Quick fill checklist** (`backend/.env`):

- `JWT_SECRET_KEY` — any long random string for local dev
- `DATABASE_URL` / `ASYNC_DATABASE_URL` — Postgres (see [Docker Compose](#run-with-docker-compose-local) for in-stack URLs)
- `REDIS_ENDPOINT` — `redis://localhost:6379` on the host; `redis://redis:6379` inside Compose
- `S3_*` — bucket and credentials (AWS or MinIO; Compose does not start object storage)
- `API_AZURE`, `API_GEMINI` — OCR pipeline (Azure Document Intelligence + Gemini)
- `OPENAI_API_KEY`, `OPENAI_MODEL` — AI grader (`API_KEY` / `MODEL` are accepted aliases)

Set `SANDBOX_HOST_TMP_PATH` in the root `.env` to an **absolute** path, e.g. `/Users/you/JavaSmartGrader/backend/sandbox/tmp`, then create the directory:

```bash
mkdir -p backend/sandbox/tmp
```

## Quick Start (host)

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package/runtime manager)
- Node.js 18+
- Redis
- PostgreSQL
- Docker (required for Java sandbox execution; optional Compose stack for Redis/Postgres/workers — see below)
- Object storage: S3-compatible bucket (e.g. MinIO locally) for student submission images; see `backend/.env.example`

### 1) Backend

```bash
cd backend
uv sync
uv run task dev
```

(`task local` and `task prod` are also defined in `backend/pyproject.toml`; see `backend/README.md`.)

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

**Tests:** from `backend/`, run the full suite with `uv run pytest`. Unit tests live in per-package `test.py` files; HTTP end-to-end tests are in `tests/test_submission.py` (marked `e2e`; requires API, DB, and S3). Skip e2e with `uv run pytest -m "not e2e"`. Details: `backend/README.md`.

### 2) Frontend

```bash
cd frontend
npm install
npm start
```

Frontend runs at [http://localhost:3000](http://localhost:3000).

## Run with Docker Compose (local)

Runs Redis, Postgres, the FastAPI API, and separate OCR / sandbox / AI grader worker containers from `backend/Dockerfile`. The API container runs Alembic migrations on startup (`backend/scripts/docker-db-init.sh`).

### Prerequisites

- Docker Engine (and Docker Desktop on macOS/Windows)
- Env files from [Environment setup](#environment-setup)
- Host path for `SANDBOX_HOST_TMP_PATH` created (`mkdir -p backend/sandbox/tmp`)
- S3-compatible storage still configured in `backend/.env` (not included in Compose)

### 1) Configure env for the stack

Root `.env` — set the sandbox mount (absolute path):

```bash
SANDBOX_HOST_TMP_PATH=/absolute/path/to/JavaSmartGrader/backend/sandbox/tmp
```

`backend/.env` — point at Compose service hostnames and the Postgres credentials defined in `docker-compose.yml`:

```bash
DATABASE_URL=postgresql://jsg_user:jsg_secure_password@postgres:5432/jsg_db
ASYNC_DATABASE_URL=postgresql+asyncpg://jsg_user:jsg_secure_password@postgres:5432/jsg_db
REDIS_ENDPOINT=redis://redis:6379
APP_ENV=dev
```

Fill in `JWT_SECRET_KEY`, `S3_*`, and provider keys as in the checklist above.

### 2) Build and start

From the repository root:

```bash
docker compose build
docker compose up
```

Detached mode: `docker compose up -d`.

| Service | Port / access |
|---------|----------------|
| API | [http://localhost:8000](http://localhost:8000) — [http://localhost:8000/docs](http://localhost:8000/docs) |
| Postgres | `localhost:5432` (`jsg_user` / `jsg_secure_password` / `jsg_db`) |
| Redis | `localhost:6379` |

The **sandbox** service mounts the host Docker socket so it can run compiler/executor images; keep Docker running on the host.

Stop and remove containers: `docker compose down`. Add `-v` to drop the Postgres volume.

### 3) Frontend (optional)

With the API up on port 8000, start the React app on the host (`cd frontend && npm start`) — see `frontend/README.md`.

## Environment notes

- Backend settings load from `backend/.env`, or `backend/.env.local` when `APP_ENV=local` (`backend/settings.py`).
- Core keys commonly needed:
  - `DATABASE_URL` / `ASYNC_DATABASE_URL`
  - `REDIS_ENDPOINT`, `QUEUE_NAMESPACE` (default `jsg.v1`)
  - Job queues: `MAIN_QUEUE`, `OCR_QUEUE`, `SANDBOX_QUEUE`, `AI_GRADING_QUEUE` (defaults match `backend/settings.py`)
  - Per-pipeline concurrency: `MAIN_MAX_CONCURRENCY`, `OCR_MAX_CONCURRENCY`, `SANDBOX_MAX_CONCURRENCY`, `AI_GRADING_MAX_CONCURRENCY`
  - `JWT_SECRET_KEY`
  - `S3_*` / `STORAGE_BACKEND` for uploads (API stores object keys on submissions; OCR reads images from the bucket)
  - `API_AZURE`, `API_GEMINI`, `GEMINI_MODEL` for OCR
  - `OPENAI_API_KEY`, `OPENAI_MODEL` for the AI grader (aliases `API_KEY`, `MODEL`)

## Documentation index

- Backend: `backend/README.md`
- API routes: `backend/api/README.md`
- Database + migrations: `backend/db/README.md`
- Alembic usage: `backend/db/alembic/README.md`
- Sandbox worker: `backend/sandbox/README.md`
- AI grader worker: `backend/ai_grader/README.md`
- OCR pipeline: `backend/ocr/README.md` (worker details: `backend/ocr/ocr_corrector/README.md`)
- Frontend: `frontend/README.md`

## Contributing

1. Create a branch from `main`.
2. Run relevant checks before pushing:
   - backend: `cd backend && uv run task lint` (formats from repo root per `pyproject.toml`); `uv run pytest -m "not e2e"` for fast tests
   - frontend: `cd frontend && npm test`
3. Open a pull request with a short test plan.

## License

This project is licensed under the MIT License. See `LICENSE`.
