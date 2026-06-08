"""Tests for logging configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from job_sentinel.config.logging import configure_logging
from job_sentinel.config.settings import LogSettings

if TYPE_CHECKING:
    from pathlib import Path


def test_configure_logging_human_mode(tmp_path: Path) -> None:
    configure_logging(LogSettings(level="DEBUG", dir=tmp_path))
    from loguru import logger

    logger.info("hello from test")
    # A log file should be created in the configured directory.
    assert (tmp_path / "sentinel.log").exists()


def test_configure_logging_json_mode(tmp_path: Path) -> None:
    # json_logs uses the LOG_JSON env alias; set it directly here.
    settings = LogSettings(level="INFO", dir=tmp_path)
    object.__setattr__(settings, "json_logs", True)
    configure_logging(settings)
    from loguru import logger

    logger.info("structured")
    assert (tmp_path / "sentinel.log").exists()
