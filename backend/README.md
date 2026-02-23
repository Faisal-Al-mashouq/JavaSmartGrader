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
├── sandbox/
│   ├── __init__.py
│   ├── sandbox_worker.py  # Async worker that processes Java compile/execute jobs
│   ├── schemas.py         # Pydantic models for jobs, results, and test cases
│   ├── TODO.md
│   ├── Dockerfile.compiler
│   ├── Dockerfile.executer
│   └── tmp/               # Temporary workspaces (created at runtime)
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

## Sandbox Worker

The sandbox worker is an async service that processes Java compilation and execution jobs from a Redis queue. It runs Docker containers in isolated environments with memory limits, network isolation, and PID limits.

### Running the Worker

```bash
python -m backend.sandbox.sandbox_worker
```

The worker supports graceful shutdown via Ctrl+C (SIGINT).

### Docker Images

Build from the project root:

```bash
# Compiler image
docker build -f backend/sandbox/Dockerfile.compiler -t compiler-image backend/sandbox/

# Executer image
docker build -f backend/sandbox/Dockerfile.executer -t executer-image backend/sandbox/
```
