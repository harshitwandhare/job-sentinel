"""
Tests for the Telegram bot command handlers.

Handlers are async closures built by ``_make_handlers``. We invoke them
directly with a fake ``Update``/``context``, a real (temp) repository, and
mocked scheduler/notifier — no Telegram connection involved.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from job_sentinel.bot.handlers import _make_handlers
from job_sentinel.config.settings import Settings
from job_sentinel.core.models import ApplicationStatus, JobPosting
from job_sentinel.db.repository import JobRepository

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("PORTAL_USERNAME", "u")
    monkeypatch.setenv("PORTAL_PASSWORD", "p")
    monkeypatch.setenv("PORTAL_JOBS_URL", "https://example.com")
    monkeypatch.setenv("KEYWORD_FILTERS", "software,engineer")
    return Settings(db_path=tmp_path / "jobs.db")


@pytest.fixture
def repo(settings: Settings) -> JobRepository:
    r = JobRepository(settings.db_path)
    yield r
    r.close()


def _update() -> tuple[object, AsyncMock]:
    reply = AsyncMock()
    message = SimpleNamespace(reply_text=reply)
    update = SimpleNamespace(message=message)
    return update, reply


def _context(args: list[str] | None = None) -> object:
    return SimpleNamespace(args=args or [])


def _handlers(settings: Settings, repo: JobRepository):
    scheduler = MagicMock()
    scheduler.trigger_now.return_value = 2
    notifier = MagicMock()
    return _make_handlers(settings, repo, scheduler, notifier), scheduler, notifier


async def test_ping_replies(settings: Settings, repo: JobRepository) -> None:
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["ping"](update, _context())
    reply.assert_awaited_once()
    assert "alive" in reply.await_args.args[0]


async def test_start_lists_commands(settings: Settings, repo: JobRepository) -> None:
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["start"](update, _context())
    text = reply.await_args.args[0]
    assert "/jobs" in text and "/stats" in text


async def test_applied_marks_status(settings: Settings, repo: JobRepository) -> None:
    repo.save_job(JobPosting(posting_id="job-1", title="SWE"))
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["applied"](update, _context(["job-1"]))
    assert repo.get_job("job-1").status == ApplicationStatus.APPLIED
    assert "applied" in reply.await_args.args[0]


async def test_applied_without_arg_shows_usage(settings: Settings, repo: JobRepository) -> None:
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["applied"](update, _context([]))
    assert "Usage" in reply.await_args.args[0]


async def test_ignore_marks_status(settings: Settings, repo: JobRepository) -> None:
    repo.save_job(JobPosting(posting_id="job-2", title="TA"))
    handlers, _, _ = _handlers(settings, repo)
    update, _reply = _update()
    await handlers["ignore"](update, _context(["job-2"]))
    assert repo.get_job("job-2").status == ApplicationStatus.IGNORED


async def test_status_unknown_id(settings: Settings, repo: JobRepository) -> None:
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["status"](update, _context(["ghost"]))
    assert "not found" in reply.await_args.args[0]


async def test_status_known_id(settings: Settings, repo: JobRepository) -> None:
    repo.save_job(JobPosting(posting_id="job-3", title="Research Asst", employer="UTD"))
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["status"](update, _context(["job-3"]))
    assert "Research Asst" in reply.await_args.args[0]


async def test_stats_reports_counts(settings: Settings, repo: JobRepository) -> None:
    repo.save_job(JobPosting(posting_id="a", title="x"))
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["stats"](update, _context())
    assert "Stats" in reply.await_args.args[0]


async def test_filters_shows_active_keywords(settings: Settings, repo: JobRepository) -> None:
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["filters"](update, _context())
    assert "software" in reply.await_args.args[0]


async def test_adapters_lists_builtins(settings: Settings, repo: JobRepository) -> None:
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["adapters"](update, _context())
    assert "12twenty" in reply.await_args.args[0]


async def test_jobs_triggers_scrape(settings: Settings, repo: JobRepository) -> None:
    handlers, scheduler, notifier = _handlers(settings, repo)
    update, _reply = _update()
    await handlers["jobs"](update, _context())
    scheduler.trigger_now.assert_called_once()
    notifier.send_jobs_list.assert_called_once()


async def test_recent_empty(settings: Settings, repo: JobRepository) -> None:
    handlers, _, notifier = _handlers(settings, repo)
    update, reply = _update()
    await handlers["recent"](update, _context())
    assert "No jobs" in reply.await_args.args[0]
    notifier.send_jobs_list.assert_not_called()


async def test_deadlines_lists_closing_soon(settings: Settings, repo: JobRepository) -> None:
    from datetime import date, timedelta

    soon = (date.today() + timedelta(days=2)).strftime("%m/%d/%Y")
    repo.save_job(JobPosting(posting_id="d1", title="Closing Soon Role", deadline=soon))
    repo.save_job(
        JobPosting(posting_id="d2", title="No Deadline Role", deadline="Apply Immediately")
    )
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["deadlines"](update, _context())
    text = reply.await_args.args[0]
    assert "Closing Soon Role" in text
    assert "No Deadline Role" not in text


async def test_deadlines_none_soon(settings: Settings, repo: JobRepository) -> None:
    repo.save_job(JobPosting(posting_id="d3", title="Far Off", deadline="12/31/2099"))
    handlers, _, _ = _handlers(settings, repo)
    update, reply = _update()
    await handlers["deadlines"](update, _context())
    assert "Nothing closing" in reply.await_args.args[0]
