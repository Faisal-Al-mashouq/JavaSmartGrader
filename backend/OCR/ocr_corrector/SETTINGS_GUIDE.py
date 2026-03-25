# ruff: noqa: N999
"""
SETTINGS INTEGRATION GUIDE
===========================

The OCR component uses the shared `settings` module (same as sandbox).
Add these fields to your existing `backend/settings.py`:

Example (if using pydantic-settings):

    class Settings(BaseSettings):
        # ... existing fields (redis_endpoint, queue_namespace, etc.) ...

        # OCR Component
        azure_key: str = ""
        azure_endpoint: str = "https://your-resource.cognitiveservices.azure.com/"
        gemini_key: str = ""
        gemini_model: str = "gemini-2.0-flash"

        class Config:
            env_file = ".env"
            extra = "ignore"


And in your .env file, add:

    AZURE_KEY=your_azure_document_intelligence_key
    AZURE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
    GEMINI_KEY=your_google_gemini_api_key
    GEMINI_MODEL=gemini-2.0-flash


The following settings are already shared with sandbox:
    - redis_endpoint
    - queue_namespace
    - max_concurrency
    - log_level
"""
