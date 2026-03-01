"""
Allow running the package directly::

    python -m ocr_corrector path/to/image.jpg
    python -m ocr_corrector --worker          # start Redis worker
"""

import argparse
import sys

from ocr_corrector.config import validate


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ocr_corrector",
        description="Handwritten Java OCR correction pipeline.",
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="Path to the image file to process.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the Gemini model (default: from GEMINI_MODEL env var).",
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Start a Redis job queue worker instead of processing a single image.",
    )
    args = parser.parse_args()

    validate()

    if args.worker:
        from ocr_corrector.tasks import run_worker
        run_worker()
        return

    if not args.image:
        parser.error("Provide an image path, or use --worker to start the queue worker.")

    from ocr_corrector.pipeline import OCRCorrectionPipeline

    pipeline = OCRCorrectionPipeline(model=args.model)
    result = pipeline.run(args.image)

    if result.status == "completed":
        print("\n" + "=" * 50)
        print("  CORRECTED CODE")
        print("=" * 50)
        print(result.corrected_code)
    else:
        print(f"\nPipeline failed: {result.error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
