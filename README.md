# JavaSmartGrader

JavaSmartGrader is an automated grading platform for handwritten Java submissions.  
It combines a FastAPI backend, async Redis workers, Docker-based Java sandboxing, OCR correction, and a React frontend.

## Repository Layout

```text
JavaSmartGrader/
├── backend/       # FastAPI API, DB layer, queue orchestration, sandbox + OCR workers
├── frontend/      # React app
├── dataset/       # LLM evaluation datasets and promptfoo configs
├── experiments/   # Experiment notes and outputs
└── model/         # Model artifacts
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package/runtime manager)
- Node.js 18+
- Redis
- PostgreSQL
- Docker (required for Java sandbox execution)

### 1) Backend

```bash
cd backend
uv sync
uv run task all
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2) Frontend

```bash
cd frontend
npm install
npm start
```

Frontend runs at [http://localhost:3000](http://localhost:3000).

## Environment Notes

- Backend settings are loaded from `backend/.env` via `pydantic-settings`.
- Core keys commonly needed:
  - `DATABASE_URL` / `ASYNC_DATABASE_URL`
  - `REDIS_ENDPOINT`
  - `JWT_SECRET_KEY`
  - provider keys (OpenAI, Anthropic, Gemini, etc.) when grading/OCR flows require them

## Documentation Index

- Backend: `backend/README.md`
- API routes: `backend/api/README.md`
- Database + migrations: `backend/db/README.md`
- Alembic usage: `backend/db/alembic/README.md`
- Sandbox worker: `backend/sandbox/README.md`
- OCR pipeline: `backend/ocr/README.md`
- Frontend: `frontend/README.md`
- LLM benchmark dataset: `dataset/LLM/Test/README.md`

## Contributing

1. Create a branch from `main`.
2. Run relevant checks before pushing:
   - backend: `cd backend && uv run task lint`
   - frontend: `cd frontend && npm test`
3. Open a pull request with a short test plan.

## License

This project is licensed under the MIT License. See `LICENSE`.
