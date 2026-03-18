from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_text(file_path: str) -> dict[str, Any]:
    """
    Thin OCR adapter.

    Replace this function with your real OCR system integration.
    Expected return format:
    {
        "text": "<extracted code>",
        "confidence": 0.0..1.0,
        "source": "existing_system|placeholder"
    }
    """
    path = Path(file_path)

    # Attempt to call existing OCR pipeline in the main codebase.
    try:
        from backend.OCR.ocr_corrector.pipeline import (
            OCRCorrectionPipeline,  # type: ignore
        )

        pipeline = OCRCorrectionPipeline()
        result = pipeline.run(path)
        extracted = (getattr(result, "corrected_code", "") or "").strip()
        confidence = 0.9 if extracted else 0.0
        return {
            "text": extracted,
            "confidence": confidence,
            "source": "existing_system",
        }
    except Exception:
        pass

    # Deterministic placeholder for local prototype behavior.
    stem = path.stem.lower()
    if "low" in stem:
        return {
            "text": (
                "// demo-level: low\n"
                "public class Main { public static void main(String[] a){ "
                "System.out.println(1/0); } }"
            ),
            "confidence": 0.42,
            "source": "placeholder",
        }
    if "mid" in stem:
        return {
            "text": (
                "// demo-level: mid\n"
                'public class Main { public static void main(String[] a){ '
                'System.out.println("MID"); } }'
            ),
            "confidence": 0.81,
            "source": "placeholder",
        }
    if "high" in stem:
        return {
            "text": (
                "// demo-level: high\n"
                'public class Main { public static void main(String[] a){ '
                'System.out.println("HIGH"); } }'
            ),
            "confidence": 0.95,
            "source": "placeholder",
        }

    if path.suffix.lower() in {".txt", ".java"} and path.exists():
        return {
            "text": path.read_text(encoding="utf-8", errors="ignore"),
            "confidence": 0.9,
            "source": "placeholder",
        }

    return {
        "text": "",
        "confidence": 0.0,
        "source": "placeholder",
    }
