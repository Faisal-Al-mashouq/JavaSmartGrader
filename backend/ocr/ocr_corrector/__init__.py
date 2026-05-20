"""
ocr_corrector — Handwritten Java OCR Correction Pipeline.

Uses Azure Document Intelligence for word-level OCR with
confidence scores, then applies Gemini LLM post-processing
to correct machine misreads while preserving student logic.

Integrates with the project's Redis job queue (matching
the sandbox component's architecture).
"""
