# Sandbox Worker

Async service that compiles and executes Java code submissions in isolated Docker containers, with test case evaluation. Jobs are consumed from a Redis queue using the same **namespace** pattern as OCR and the AI grader (`QUEUE_NAMESPACE` in `backend/settings.py`).

## Architecture

```
Redis Queue (`jsg.v1:SandboxJobQueue`)
        │
        ▼
  Sandbox Worker (async, N concurrent coroutines)
        │
        ├── 1. Compile  →  Docker (compiler-image, JDK 21)
        ├── 2. Execute   →  Docker (executer-image, JRE 21) per test case
        └── 3. Evaluate  →  Compare actual vs expected output
        │
        ▼
  Result pushed to `jsg.v1:SandboxJobQueue:completed:{job_id}`
```

Each Docker container runs with:
- 256MB memory limit
- No network access
- PID limit of 50
- Read-only filesystem (executer only)

## Prerequisites

- Docker
- Redis
- Python 3.12+

## Setup

1. Create a `.env` file in `backend/sandbox/` (or `backend/`):

```
REDIS_ENDPOINT="redis://<user>:<password>@localhost:6379"
QUEUE_NAMESPACE="jsg.v1"
MAX_CONCURRENCY=10
```

2. Docker images are built automatically on worker startup. To build manually:

```bash
# From project root
docker build -f backend/sandbox/docker/Dockerfile.compiler -t compiler-image backend/sandbox/docker
docker build -f backend/sandbox/docker/Dockerfile.executer -t executer-image backend/sandbox/docker
```

## Running

Start the worker (recommended, from `backend/`):

```bash
uv run task sandbox
```

Or directly:

```bash
python -m sandbox.sandbox_worker
```

Push test jobs to the queue (from `backend/`):

```bash
python -m sandbox.test_jobs
```
Run docker containers via commands per {CLASS_NAME} (for testing):

```bash
# From project root
docker run --rm -v $(pwd)/backend/sandbox/tmp/test:/workspace --memory=256m --network=none --pids-limit=50 compiler-image sh /scripts/compile.sh {CLASS_NAME}

docker run --rm -v $(pwd)/backend/sandbox/tmp/test:/workspace --memory=256m --network=none --pids-limit=50 --read-only executer-image sh /scripts/execute.sh {CLASS_NAME} > $(pwd)/backend/sandbox/tmp/test/out/output.txt 2> $(pwd)/backend/sandbox/tmp/test/out/errors.txt
```

The worker supports graceful shutdown via `Ctrl+C`.

## Module Structure

| File | Purpose |
|------|---------|
| `sandbox_worker.py` | Main loop, job lifecycle orchestration |
| `jobs.py` | Compile, execute, and test case evaluation logic |
| `helpers.py` | Workspace management, Docker container commands |
| `schemas.py` | Pydantic models for jobs, requests, and results |
| `test_jobs.py` | Pushes sample jobs to Redis for testing |

## Job Payload Format

Push a JSON string to the `jsg.v1:SandboxJobQueue` Redis list:

```json
{
    "job_id": "uuid",
    "java_code": "public class Main { ... }",
    "test_cases": {
        "test_cases": [
            {"input": "1 2", "expected_output": "3"}
        ]
    }
}
```

- `input` is fed via stdin (not command-line args)
- `test_cases` can be `null` for no assertions
- The public class name is auto-extracted from the code
