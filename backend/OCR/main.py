"""
Entry point for the OCR worker.

Usage::

    python main.py
"""

import asyncio

from ocr_corrector.ocr_worker import start

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
