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

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package/runtime manager)
- Node.js 18+
- Redis
- PostgreSQL
- Docker (required for Java sandbox execution; optional Compose stack for Redis/Postgres/workers — see `docker-compose.yml` at the repo root)
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

## Environment Notes

- Backend settings are loaded from `backend/.env` (or `backend/.env.local` when `APP_ENV=local`) via `pydantic-settings`; start from `backend/.env.example`.
- Core keys commonly needed:
  - `DATABASE_URL` / `ASYNC_DATABASE_URL`
  - `REDIS_ENDPOINT`, `QUEUE_NAMESPACE` (default `jsg.v1`)
  - Job queues: `MAIN_QUEUE`, `OCR_QUEUE`, `SANDBOX_QUEUE`, `AI_GRADING_QUEUE` (defaults match `backend/settings.py`)
  - Per-pipeline concurrency: `MAIN_MAX_CONCURRENCY`, `OCR_MAX_CONCURRENCY`, `SANDBOX_MAX_CONCURRENCY`, `AI_GRADING_MAX_CONCURRENCY`
  - `JWT_SECRET_KEY`
  - `S3_*` / `STORAGE_BACKEND` for uploads (API stores object keys on submissions; OCR reads images from the bucket)
  - Provider keys (`API_AZURE`, `API_GEMINI`, `API_KEY` / `MODEL` for the AI grader, etc.) when grading/OCR flows require them

## Documentation Index

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
