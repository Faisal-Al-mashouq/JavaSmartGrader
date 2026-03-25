# OCR Corrector — Job Queue Worker

Async service that extracts and corrects handwritten Java code from exam images using Azure OCR + Gemini LLM, with automatic flagging of uncertain words. Jobs are consumed from a Redis queue.

## Architecture

```
Redis Queue (`jsg.v1:OCRJobQueue`)
        │
        ▼
  OCR Worker (async, N concurrent coroutines)
        │
        ├── 1. OCR Extract   →  Azure Document Intelligence (high-res)
        ├── 2. LLM Correct   →  Gemini (confidence-aware correction)
        └── 3. Flag Detect   →  Uncertain words → ConfidenceFlag records
        │
        ▼
  Result pushed to `jsg.v1:OCRJobQueue:completed:{job_id}` (TTL 1h)
  API layer persists flags via create_confidence_flag()
```

## Prerequisites

- Redis
- Python 3.12+
- Azure Document Intelligence API key
- Google Gemini API key

## Setup

Add these to your shared `backend/.env`:

```
API_AZURE=your_azure_document_intelligence_key
AZURE_OCR_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
API_GEMINI=your_google_gemini_api_key
# GEMINI_MODEL=gemini-3.1-flash-preview  (optional override)

# Shared with sandbox:
REDIS_ENDPOINT=redis://localhost:6379/0
QUEUE_NAMESPACE=jsg.v1
MAX_CONCURRENCY=5
```

## Running

Start the worker (from `backend/OCR/`):

```bash
python main.py
```

Push test jobs to the queue:

```bash
python -m ocr_corrector.test_jobs
```

## Module Structure

| File | Purpose |
|------|---------|
| `ocr_worker.py` | Main loop, job lifecycle orchestration |
| `jobs.py` | OCR extraction, LLM correction, flag detection step functions |
| `helpers.py` | Azure OCR client, Gemini client, response parsing |
| `schemas.py` | Pydantic models for jobs, requests, results, and flags |
| `prompts.py` | LLM system prompt and user input formatter |
| `logs.py` | Rich logging setup |
| `test_jobs.py` | Pushes sample jobs to Redis for testing |
| `tests.py` | Unit tests |
| `SETTINGS_GUIDE.py` | Settings field reference |

## Job Payload Format

Push a JSON string to the `jsg.v1:OCRJobQueue` Redis list:

```json
{
    "job_id": "uuid",
    "image_path": "/uploads/exam_001.jpg",
    "submission_id": "uuid-or-null",
    "transcription_id": 42
}
```

- `transcription_id` is the FK to the existing transcription record — the API layer needs it to call `create_confidence_flag()`

## Flag Detection

Words are flagged when the LLM reports it cannot confidently determine the correct reading. Each flagged word becomes an `OCRFlag` with up to 5 ranked suggestions.

Each `OCRFlag` in the job result maps directly to the existing `ConfidenceFlag` DB table:

| OCRFlag field | ConfidenceFlag column | Description |
|---|---|---|
| `text_segment` | `text_segment` | The original OCR-extracted word |
| `confidence_score` | `confidence_score` | Azure confidence as Decimal (0.00–1.00) |
| `coordinates` | `coordinates` | Position string: `"line:3:word:2"` |
| `suggestions` | `suggestions` | Comma-separated ranked suggestions from the LLM |

## API Layer Integration

When the API route consumes an OCR job result from Redis, persist any flags using the existing CRUD:

```python
from api.crud.confidence_flags import create_confidence_flag

# After reading OCRJobResult from Redis:
if result.result and result.result.flag_result:
    for flag in result.result.flag_result.flags or []:
        await create_confidence_flag(
            session=session,
            transcription_id=result.transcription_id,
            text_segment=flag.text_segment,
            confidence_score=flag.confidence_score,
            coordinates=flag.coordinates,
            suggestions=flag.suggestions,
        )
```

No new DB models or migrations needed — flags flow directly into the existing `ConfidenceFlag` table.

## Comparison with Sandbox Component

| Aspect | Sandbox | OCR Corrector |
|--------|---------|---------------|
| Queue | `jsg.v1:SandboxJobQueue` | `jsg.v1:OCRJobQueue` |
| Worker | `sandbox_worker.py` | `ocr_worker.py` |
| Steps | Compile → Execute → Test | OCR → LLM Correct → Flag |
| Schemas | Pydantic (`SandboxJob`) | Pydantic (`OCRJob`) |
| Concurrency | N async coroutines | N async coroutines |
| Results | Redis completed queue | Redis completed queue + TTL |
| Extra | Docker containers | Flags → ConfidenceFlag DB table |
