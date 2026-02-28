# JavaSmartGrader Backend

Python backend service for the JavaSmartGrader application.

## Requirements

- Python 3.12+

## Installation

```bash
cd backend
pip install -e .
```

## Running the Server

```bash
python main.py
```

## Project Structure

```
backend/
├── main.py              # Application entry point
├── pyproject.toml       # Project configuration and dependencies
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
│   ├── __init__.py
│   ├── sandbox_worker.py  # Async worker orchestrator (main loop, job lifecycle)
│   ├── jobs.py            # Job processing (compile, execute, test case evaluation)
│   ├── helpers.py         # Workspace management, Docker container commands
│   ├── schemas.py         # Pydantic models for jobs, results, and test cases
│   ├── test_jobs.py       # Script to push test payloads to Redis queue
│   ├── TODO.md
│   ├── Dockerfile.compiler
│   ├── Dockerfile.executer
│   └── tmp/               # Temporary workspaces and test results (created at runtime)
└── README.md            # This file
```

## Development

### Adding Dependencies

Edit `pyproject.toml` to add new dependencies:

```toml
[project]
dependencies = [
    "fastapi",
    "uvicorn",
]
```

Then reinstall:

```bash
pip install -e .
```

### Running Tests

```bash
pytest
```

## API Endpoints

*API endpoints will be documented here as they are developed.*

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8000` |
| `DEBUG` | Enable debug mode | `false` |
| `REDIS_ENDPOINT` | Redis connection URL for sandbox job queue | — |
| `DATABASE_URL` | PostgreSQL async connection URL | — |

## Database

Async PostgreSQL database using SQLAlchemy 2.0 ORM with Alembic migrations.

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

The sandbox worker is an async service that processes Java compilation and execution jobs from a Redis queue. It runs Docker containers in isolated environments with memory limits, network isolation, and PID limits.

### Running the Worker

```bash
python -m backend.sandbox.sandbox_worker
```

The worker supports graceful shutdown via Ctrl+C (SIGINT).

### Docker Images

Docker images (`compiler-image` and `executer-image`) are built automatically when the worker starts.

To build them manually from the project root:

```bash
# Compiler image
docker build -f backend/sandbox/Dockerfile.compiler -t compiler-image backend/sandbox/

# Executer image
docker build -f backend/sandbox/Dockerfile.executer -t executer-image backend/sandbox/
```
