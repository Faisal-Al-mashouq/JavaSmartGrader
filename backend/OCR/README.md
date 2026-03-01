# Handwritten Java OCR Correction Pipeline

A two-stage pipeline that corrects OCR misreads in handwritten Java exam submissions while preserving student logic errors.

**Stage 1 — Azure Document Intelligence:** Extracts every word with a confidence score using high-resolution OCR.

**Stage 2 — Gemini LLM Correction:** Uses confidence-annotated text to distinguish machine misreads (fix them) from student mistakes (keep them).

## Project Structure

```
ocr_corrector/
├── __init__.py        # Package exports
├── __main__.py        # CLI entry point (python -m ocr_corrector)
├── config.py          # Environment variables and validation
├── models.py          # Data classes (OCRWord, OCRLine, CorrectionResult)
├── ocr_engine.py      # Azure Document Intelligence integration
├── llm_corrector.py   # Gemini API integration
├── pipeline.py        # Orchestrates OCR → LLM → result
├── prompts.py         # LLM prompt templates (easy to iterate)
└── tasks.py           # Redis job queue worker
main.py                # Root entry point
.env.template          # API key template
requirements.txt       # Python dependencies
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.template .env
# Edit .env with your Azure and Gemini keys
```

## Usage

### Direct (single image)

```bash
python main.py path/to/exam_image.jpg

# Or as a module
python -m ocr_corrector path/to/exam_image.jpg

# Override model
python -m ocr_corrector image.jpg --model gemini-2.5-flash
```

### From Python

```python
from ocr_corrector import OCRCorrectionPipeline

pipeline = OCRCorrectionPipeline()
result = pipeline.run("exam_scan.jpg")

print(result.status)          # "completed"
print(result.corrected_code)  # Corrected Java code
print(result.raw_ocr_text)    # Raw OCR before correction
print(result.to_dict())       # Serializable dict for APIs
```

### Redis Job Queue

For processing multiple images asynchronously (e.g., from a web server):

```bash
# Start the worker (blocks, processing jobs from Redis)
python -m ocr_corrector --worker
```

```python
# Enqueue jobs from your API server
from ocr_corrector.tasks import enqueue_job, get_job_status, get_job_result

job_id = enqueue_job("/uploads/exam_001.jpg")

status = get_job_status(job_id)   # "pending" → "processing" → "completed"
result = get_job_result(job_id)   # dict with corrected_code, raw_ocr_text, etc.
```

## How It Works

1. Azure OCR scans the image and returns each word with a confidence percentage:
   ```
   publIc[45] Class[99] term[92] 5[30]
   ```

2. The LLM uses confidence scores to decide what to fix:
   - `publIc[45]` → low confidence + near keyword → fix to `public`
   - `5[30]` → low confidence + likely `{` misread → fix to `{`
   - `term[92]` → high confidence → keep as-is (student's choice)

3. Student logic errors are preserved. If a student writes an infinite loop, wrong variable name, or missing semicolon — the pipeline keeps it.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_AZURE` | Yes | — | Azure Document Intelligence key |
| `API_GEMINI` | Yes | — | Google Gemini API key |
| `AZURE_ENDPOINT` | No | Project default | Azure endpoint URL |
| `GEMINI_MODEL` | No | `gemini-3.1-flash-preview` | Gemini model to use |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_QUEUE_NAME` | No | `ocr:jobs` | Redis queue name |
| `REDIS_RESULT_TTL` | No | `3600` | Result expiry in seconds |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
