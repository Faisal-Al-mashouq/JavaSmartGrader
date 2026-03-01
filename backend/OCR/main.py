"""
CLI entry point for the OCR correction pipeline.

Usage::

    python main.py path/to/image.jpg
    python main.py path/to/image.jpg --model gemini-2.5-flash
    python main.py --worker
"""

from ocr_corrector.__main__ import main

if __name__ == "__main__":
    main()
