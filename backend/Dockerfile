FROM python:3.12-slim AS base
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS backend
COPY . .
CMD ["uv", "run", "task", "prod"]

FROM base AS ocr
COPY . .
CMD ["uv", "run", "python", "-m", "ocr.main"]

FROM base AS sandbox
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*
COPY . .
CMD ["uv", "run", "python", "-m", "sandbox.sandbox_worker"]

FROM base AS ai_grader
COPY . .
CMD ["uv", "run", "python", "-m", "ai_grader.main"]
