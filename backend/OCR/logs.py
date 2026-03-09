import logging

from rich.logging import RichHandler
from settings import settings


def setup_logging(level: str | None = None) -> None:
    level_name = (level or settings.log_level).upper()

    logging.basicConfig(
        level=level_name,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
