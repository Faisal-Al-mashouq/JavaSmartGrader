import logging
import os

from rich.logging import RichHandler


def setup_logging(level: str | None = None) -> None:
    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    logging.basicConfig(
        level=level_name,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
