"""
config/logging.py
─────────────────
Application logging setup using **loguru**.

Why loguru over stdlib logging?
  • Zero-config beautiful console output with colours + tracebacks
  • Structured JSON mode for log aggregators (Loki, Datadog, Grafana)
  • Rotating file handler in one line, no RotatingFileHandler boilerplate
  • Context binding: logger.bind(posting_id=x).info("found")
  • Inter-process safe (no threading.Lock boilerplate)

Call ``configure_logging(settings)`` exactly once at startup (main.py).
Then in every module just:

    from loguru import logger
    logger.info("hello {name}", name="world")
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from job_sentinel.config.settings import LogSettings


def configure_logging(log_settings: LogSettings) -> None:
    """
    Remove loguru defaults and install project handlers.

    Parameters
    ----------
    log_settings:
        The ``LogSettings`` subsection from :func:`~job_sentinel.config.settings.get_settings`.
    """
    # Remove loguru's default stderr handler
    logger.remove()

    level = log_settings.level  # e.g. "INFO"
    log_file = log_settings.dir / "sentinel.log"

    # ── Console handler ────────────────────────────────────────────────────
    if log_settings.json_logs:
        # Structured JSON — useful when running inside a container or
        # piping logs into a collector (Loki, Datadog, etc.)
        logger.add(
            sys.stderr,
            level=level,
            serialize=True,  # loguru's built-in JSON serializer
            backtrace=False,
            diagnose=False,
        )
    else:
        # Human-readable coloured output for development / direct WSL use
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level:<8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
                "<level>{message}</level>"
            ),
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # ── Rotating file handler ──────────────────────────────────────────────
    # 5 MB per file, keep 3 backups = max ~15 MB on disk
    logger.add(
        str(log_file),
        level=level,
        rotation="5 MB",
        retention=3,
        compression="gz",  # compress old logs — zero extra deps
        serialize=log_settings.json_logs,
        backtrace=True,
        diagnose=False,  # don't leak variable values in prod files
        enqueue=True,  # async-safe writes
    )

    logger.info("Logging configured | level={} | file={}", level, log_file)
