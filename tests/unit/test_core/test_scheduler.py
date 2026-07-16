"""Unit tests for the APScheduler wrapper.

These isolate ``Scheduler`` from the real DB and browser (see
``tests/integration/test_scheduler_cycle.py`` for the full pipeline against a
real ``JobRepository``) and focus on lifecycle, error handling, and the
closed-posting sweep.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

import pytest

from job_sentinel.config.settings import Settings
from job_sentinel.core import scheduler as scheduler_mod
from job_sentinel.core.models import ApplicationStatus, JobPosting
from job_sentinel.core.scheduler import Scheduler

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from job_sentinel.db.repository import JobRepository


class _FakeRepo:
    """Minimal stand-in for JobRepository — in-memory, no SQLite."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobPosting] = {}
        self._status: dict[str, ApplicationStatus] = {}

    def save_job(self, job: JobPosting) -> bool:
        is_new = job.posting_id not in self._jobs
        self._jobs[job.posting_id] = job
        if is_new:
            self._status[job.posting_id] = ApplicationStatus.NEW
        return is_new

    def get_by_status(self, status: ApplicationStatus) -> list[JobPosting]:
        return [
            job for posting_id, job in self._jobs.items() if self._status.get(posting_id) == status
        ]

    def update_status(self, posting_id: str, status: ApplicationStatus) -> None:
        self._status[posting_id] = status


def _make_scheduler(
    settings: Settings, repo: _FakeRepo, on_new_jobs: scheduler_mod.NotifyCallback
) -> Scheduler:
    """Build a Scheduler against the in-memory fake repo (cast for mypy)."""
    return Scheduler(settings, cast("JobRepository", repo), on_new_jobs)


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("PORTAL_USERNAME", "u")
    monkeypatch.setenv("PORTAL_PASSWORD", "p")
    monkeypatch.setenv("PORTAL_JOBS_URL", "https://example.com")
    monkeypatch.setenv("KEYWORD_FILTERS", "")
    return Settings(db_path=tmp_path / "jobs.db", dry_run=False)


@contextmanager
def _fake_ctx(_scraper: object, storage_state: object = None) -> Iterator[object]:
    yield object()


def _patch_scrape(monkeypatch: pytest.MonkeyPatch, jobs: list[JobPosting]) -> None:
    class _FakeAdapter:
        def scrape(self, _context: object) -> list[JobPosting]:
            return jobs

    monkeypatch.setattr(scheduler_mod, "browser_context", _fake_ctx)
    monkeypatch.setattr(scheduler_mod, "get_adapter", lambda _id, _scraper: _FakeAdapter())


class TestLifecycle:
    def test_not_running_before_start(self, settings: Settings) -> None:
        sched = _make_scheduler(settings, _FakeRepo(), lambda _jobs: None)
        assert sched.running is False

    def test_start_registers_job_and_runs_immediately(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_scrape(monkeypatch, [])
        sched = _make_scheduler(settings, _FakeRepo(), lambda _jobs: None)

        calls: list[int] = []

        def _fake_trigger_now() -> int:
            calls.append(1)
            return 0

        monkeypatch.setattr(sched, "trigger_now", _fake_trigger_now)

        sched.start()
        try:
            assert sched.running is True
            assert sched._scheduler.get_job("scrape_cycle") is not None
            assert calls == [1]  # trigger_now called once on start
        finally:
            sched.stop()

    def test_stop_is_safe_when_never_started(self, settings: Settings) -> None:
        sched = _make_scheduler(settings, _FakeRepo(), lambda _jobs: None)
        sched.stop()  # must not raise
        assert sched.running is False

    def test_stop_after_start_shuts_down(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_scrape(monkeypatch, [])
        sched = _make_scheduler(settings, _FakeRepo(), lambda _jobs: None)
        sched.start()
        sched.stop()
        assert sched.running is False


class TestRunCycleAndTriggerNow:
    def test_trigger_now_returns_new_count(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_scrape(monkeypatch, [JobPosting(posting_id="a", title="SWE", source_adapter="x")])
        sched = _make_scheduler(settings, _FakeRepo(), lambda _jobs: None)
        assert sched.trigger_now() == 1

    def test_run_cycle_returns_full_result(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_scrape(monkeypatch, [JobPosting(posting_id="a", title="SWE", source_adapter="x")])
        sched = _make_scheduler(settings, _FakeRepo(), lambda _jobs: None)
        result = sched.run_cycle()
        assert result.new_count == 1
        assert result.total_scraped == 1
        assert result.errors == []


class TestErrorHandling:
    def test_adapter_exception_is_captured_not_raised(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(_id: str, _scraper: object) -> None:
            raise RuntimeError("adapter unavailable")

        monkeypatch.setattr(scheduler_mod, "browser_context", _fake_ctx)
        monkeypatch.setattr(scheduler_mod, "get_adapter", _boom)

        sched = _make_scheduler(settings, _FakeRepo(), lambda _jobs: None)
        result = sched.run_cycle()

        assert result.errors == ["adapter unavailable"]
        assert result.new_count == 0
        assert result.duration_seconds >= 0.0

    def test_empty_scrape_returns_early_without_notifying(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_scrape(monkeypatch, [])
        notified: list[list[JobPosting]] = []
        sched = _make_scheduler(settings, _FakeRepo(), notified.append)

        result = sched.run_cycle()

        assert result.total_scraped == 0
        assert result.new_count == 0
        assert notified == []


class TestMarkClosed:
    def test_marks_missing_open_postings_closed(self, settings: Settings) -> None:
        repo = _FakeRepo()
        repo.save_job(JobPosting(posting_id="a", title="SWE", source_adapter="x"))
        repo.save_job(JobPosting(posting_id="b", title="TA", source_adapter="x"))

        sched = _make_scheduler(settings, repo, lambda _jobs: None)
        closed = sched._mark_closed([JobPosting(posting_id="a", title="SWE", source_adapter="x")])

        assert closed == 1
        assert repo._status["b"] == ApplicationStatus.CLOSED
        assert repo._status["a"] == ApplicationStatus.NEW

    def test_no_postings_missing_marks_nothing(self, settings: Settings) -> None:
        repo = _FakeRepo()
        repo.save_job(JobPosting(posting_id="a", title="SWE", source_adapter="x"))

        sched = _make_scheduler(settings, repo, lambda _jobs: None)
        closed = sched._mark_closed([JobPosting(posting_id="a", title="SWE", source_adapter="x")])

        assert closed == 0
        assert repo._status["a"] == ApplicationStatus.NEW
