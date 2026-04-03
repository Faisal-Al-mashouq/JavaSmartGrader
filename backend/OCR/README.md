# Handwritten Java OCR Correction Pipeline

A two-stage pipeline that corrects OCR misreads in handwritten Java exam submissions while preserving student logic errors. Runs as an async Redis job queue worker, mirroring the sandbox component's architecture.

**Stage 1 — Azure Document Intelligence:** Extracts every word with a confidence score using high-resolution OCR.

**Stage 2 — Gemini LLM Correction:** Uses confidence-annotated text to distinguish machine misreads (fix them) from student mistakes (keep them). Uncertain words are flagged for manual review.

## Project Structure

```
backend/ocr/
├── main.py                        # Entry point — starts the async worker
├── requirements.txt               # Optional legacy standalone deps
├── .env.template                  # API key template (optional)
└── ocr_corrector/
    ├── __init__.py                # Package docstring
    ├── ocr_worker.py              # Async Redis worker — job lifecycle
    ├── jobs.py                    # OCR, LLM, and flag-detection step functions
    ├── helpers.py                 # Azure OCR and Gemini API clients
    ├── schemas.py                 # Pydantic models for jobs, results, and flags
    ├── prompts.py                 # LLM prompt templates
    ├── logs.py                    # Rich logging setup
    ├── test_jobs.py               # Pushes sample jobs to Redis for testing
    ├── tests.py                   # Unit tests
    └── SETTINGS_GUIDE.py          # Settings integration reference
```

## Queue Architecture

```
API layer pushes job JSON
        │
        ▼
{namespace}:OCRJobQueue                   (pending)
        │  blmove (atomic)
        ▼
{namespace}:OCRJobQueue:processing        (in-progress)
        │
        ├── Step 1: Azure OCR extraction
        ├── Step 2: Gemini LLM correction
        └── Step 3: Flag detection
        │
        ▼
{namespace}:OCRJobQueue:completed:{job_id}  (result, TTL 1h)
```

## Setup

Prefer running from **`backend/`** with `uv sync` so dependencies match the rest of the stack. A legacy `requirements.txt` under `backend/OCR/` may exist for standalone use.

The OCR worker loads **`backend/settings.py`**. Document Intelligence reads submission images from the configured **S3 bucket** using the `image_path` field on each job, which must be an **object key** (for example `submissions/42/page.png`), not a local filesystem path.

Add or confirm these keys in `backend/.env`:

```
API_AZURE=your_azure_document_intelligence_key
AZURE_OCR_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
API_GEMINI=your_google_gemini_api_key

# Same object storage as the API (see backend/.env.example)
S3_BUCKET=submissions-local
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_ENDPOINT_URL=http://localhost:9000
```

## Running

From `backend/`:

```bash
uv run python -m ocr.main
```

The worker starts N concurrent coroutines (configured by `OCR_MAX_CONCURRENCY`) and blocks waiting for jobs.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_AZURE` | Yes | — | Azure Document Intelligence key |
| `AZURE_OCR_ENDPOINT` | Yes | — | Azure endpoint URL |
| `API_GEMINI` | Yes | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-3.1-flash-lite-preview` | Gemini model to use |
| `REDIS_ENDPOINT` | No | `redis://localhost:6379` | Redis connection URL |
| `QUEUE_NAMESPACE` | No | `jsg.v1` | Redis key prefix |
| `OCR_QUEUE` | No | `OCRJobQueue` | Base OCR queue name (effective queue: `{QUEUE_NAMESPACE}:{OCR_QUEUE}`) |
| `OCR_MAX_CONCURRENCY` | No | `5` | Number of parallel worker coroutines |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |

## How It Works

1. Azure OCR scans the image and returns each word with a confidence percentage:
   ```
   publIc[45] class[99] term[92] 5[30]
   ```

2. The LLM uses confidence scores to decide what to fix:
   - `publIc[45]` — low confidence + near keyword → fixed to `public`
   - `5[30]` — low confidence + unclear → left as-is, 5 ranked suggestions produced
   - `term[92]` — high confidence → kept as-is (student's choice)

3. Student logic errors are preserved. Infinite loops, wrong variable names, missing semicolons — the pipeline keeps them all.

4. Words the LLM cannot confidently correct are returned as `OCRFlag` records, ready to be persisted to the `ConfidenceFlag` DB table by the API layer.

## Testing

```bash
# From backend/
uv run pytest ocr/ocr_corrector/tests.py -v

# Push live test jobs to Redis
uv run python -m ocr.ocr_corrector.test_jobs
```
