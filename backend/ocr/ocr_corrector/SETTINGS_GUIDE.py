# ruff: noqa: N999
"""
SETTINGS INTEGRATION GUIDE
===========================

The OCR component uses the shared `settings` module at backend/settings.py.
No new fields need to be added — the required fields already exist:

    Field in settings.py       Env var           Purpose
    ─────────────────────────  ────────────────  ──────────────────────────
    api_azure                  API_AZURE         Azure Document Intelligence key
    azure_ocr_endpoint         AZURE_OCR_ENDPOINT  Azure OCR endpoint URL
    api_gemini                 API_GEMINI        Google Gemini API key
    gemini_model               GEMINI_MODEL      Gemini model (default: gemini-3.1flashpreview)

The following settings are shared with the sandbox component:
    - redis_endpoint      → REDIS_ENDPOINT
    - queue_namespace     → QUEUE_NAMESPACE
    - ocr_max_concurrency → OCR_MAX_CONCURRENCY
    - log_level           → LOG_LEVEL

In your backend/.env file, ensure these are set:

    API_AZURE=your_azure_document_intelligence_key
    AZURE_OCR_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
    API_GEMINI=your_google_gemini_api_key
    # GEMINI_MODEL=gemini-3.1-flash-preview  (optional override)
"""
