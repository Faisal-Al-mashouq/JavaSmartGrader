# JavaSmartGrader Backend

Python backend service for the JavaSmartGrader application.

## Requirements

- Python 3.12+
- PostgreSQL
- Redis
- Docker (for sandbox worker)

## Installation

```bash
cd backend
pip install -e .
```

## Running the Server

```bash
uvicorn main:app --reload
```

The API runs at http://localhost:8000. Interactive docs are available at http://localhost:8000/docs.

## Project Structure

```
backend/
├── main.py              # FastAPI application entry point and router registration
├── pyproject.toml       # Project configuration and dependencies
├── api/
│   ├── auth.py          # JWT creation, token verification, role enforcement
│   ├── dependencies.py  # Shared FastAPI dependencies (DB session)
│   └── routes/
│       ├── users.py         # /users — register, login, profile
│       ├── assignments.py   # /assignments — CRUD + testcase management
│       ├── submissions.py   # /submissions — student submission lifecycle
│       └── grading.py       # /grading — compile results, AI feedback, grades
├── db/
│   ├── models/
│   │   ├── base.py          # Declarative base
│   │   ├── main_db.py       # ORM models (User, Assignment, Submission, etc.)
│   │   └── __init__.py      # Re-exports models
│   ├── crud/
│   │   ├── users.py         # User CRUD
│   │   ├── assignments.py   # Assignment CRUD
│   │   ├── submissions.py   # Submission CRUD
│   │   ├── grading.py       # Testcase, CompileResult, Transcription, AIFeedback, Grade CRUD
│   │   └── __init__.py      # Re-exports all CRUD functions
│   ├── alembic/             # Migration versions
│   ├── alembic.ini          # Alembic configuration
│   └── session.py           # Async engine and session factory
├── sandbox/
│   ├── sandbox_worker.py  # Async worker orchestrator (main loop, job lifecycle)
│   ├── jobs.py            # Job processing (compile, execute, test case evaluation)
│   ├── helpers.py         # Workspace management, Docker container commands
│   ├── schemas.py         # Pydantic models for jobs, results, and test cases
│   ├── test_jobs.py       # Script to push test payloads to Redis queue
│   ├── Dockerfile.compiler
│   ├── Dockerfile.executer
│   └── tmp/               # Temporary workspaces and test results (created at runtime)
└── README.md            # This file
```

## Configuration

Create a `.env` file in `backend/`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/smartgrader
REDIS_ENDPOINT=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key
```

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async connection URL | — |
| `REDIS_ENDPOINT` | Redis connection URL for sandbox job queue | — |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | — |

## API

See [api/README.md](api/README.md) for full endpoint documentation.

The API is organized into four routers:

| Prefix | Description |
|--------|-------------|
| `/users` | Registration, login, profile management |
| `/assignments` | Assignment and testcase CRUD (instructors) |
| `/submissions` | Submission lifecycle (students and instructors) |
| `/grading` | Compile results, transcriptions, AI feedback, grades |

## Database

Async PostgreSQL using SQLAlchemy 2.0 ORM with Alembic migrations.

### Models

- **User** - Students and instructors (role-based)
- **Assignment** - Questions, test cases, due dates, rubrics
- **Submission** - Student work linked to assignments (state: submitted/processing/graded/failed)
- **Testcase** - Input/output pairs per assignment
- **CompileResult** - Compilation and runtime results per submission
- **Transcription** - OCR/transcription output per submission
- **AIFeedback** - AI-suggested grade and feedback per submission
- **Grade** - Final instructor grade per submission

### Migrations

```bash
# Generate migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

See [db/README.md](db/README.md) for full details.

## Sandbox Worker

Async service that compiles and executes Java submissions in isolated Docker containers, consuming jobs from a Redis queue.

### Running the Worker

```bash
python -m backend.sandbox.sandbox_worker
```

The worker supports graceful shutdown via Ctrl+C (SIGINT).

### Docker Images

Built automatically on worker startup. To build manually from the project root:

```bash
docker build -f backend/sandbox/Dockerfile.compiler -t compiler-image backend/sandbox/
docker build -f backend/sandbox/Dockerfile.executer -t executer-image backend/sandbox/
```

See [sandbox/README.md](sandbox/README.md) for full details.

## Development

### Adding Dependencies

Edit `pyproject.toml`, then reinstall:

```bash
pip install -e .
```

### Running Tests

```bash
pytest
```
