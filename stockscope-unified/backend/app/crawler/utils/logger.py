"""
crawler_v2/utils/logger.py — Logging setup using loguru.
"""

import sys

from loguru import logger

from crawler_v2.config import LOG_LEVEL, LOGS_DIR


def setup_logger() -> None:
    """Configure loguru with console + file sinks."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )
    logger.add(
        f"{LOGS_DIR}/crawler_v2_{{time:YYYY-MM-DD}}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )
