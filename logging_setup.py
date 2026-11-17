"""Configures loguru once, at startup. Docker collects whatever goes to stdout."""

import sys

from loguru import logger


def setup_logging(level: str) -> None:
    logger.remove()  # drop loguru's default handler
    logger.add(
        sys.stdout,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {message}",
    )