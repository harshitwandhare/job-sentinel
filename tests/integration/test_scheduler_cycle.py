"""
Integration test for the scrape cycle.

The browser and the site adapter are mocked, but the real ``JobRepository``
(SQLite on a temp path) and the real ``Scheduler`` orchestration run. This
exercises the filter → diff → persist → notify → close pipeline end to end
without touching the network or launching Chromium.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import pytest

from job_sentinel.config.settings import Settings
from job_sentinel.core import scheduler as scheduler_mod
from job_sentinel.core.models import ApplicationStatus, JobPosting
from job_sentinel.core.scheduler import Scheduler
from job_sentinel.db.repository import JobRepository

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("PORTAL_USERNAME", "u")
    monkeypatch.setenv("PORTAL_PASSWORD", "p")
    monkeypatch.setenv("PORTAL_JOBS_URL", "https://example.com")
    monkeypatch.setenv("KEYWORD_FILTERS", "")
    s = Settings(db_path=tmp_path / "jobs.db")
    return s


class _FakeAdapter:
    """Stands in for a real SiteAdapter — returns a scripted set of postings."""

    def __init__(self, jobs: list[JobPosting]) -> None:
        self._jobs = jobs

    def scrape(self, _context: object) -> list[JobPosting]:
        return self._jobs


def _patch_browser_and_adapter(monkeypatch: pytest.MonkeyPatch, jobs: list[JobPosting]) -> None:
    @contextmanager
    def _fake_ctx(_scraper):
        yield object()

    monkeypatch.setattr(scheduler_mod, "browser_context", _fake_ctx)
    monkeypatch.setattr(scheduler_mod, "get_adapter", lambda _id, _scraper: _FakeAdapter(jobs))


def test_new_jobs_are_persisted_and_notified(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs = [
        JobPosting(posting_id="a", title="SWE", source_adapter="12twenty"),
        JobPosting(posting_id="b", title="TA", source_adapter="12twenty"),
    ]
    _patch_browser_and_adapter(monkeypatch, jobs)

    repo = JobRepository(settings.db_path)
    notified: list[list[JobPosting]] = []
    sched = Scheduler(settings, repo, notified.append)

    result = sched._scrape_cycle()

    assert result.new_count == 2
    assert result.total_scraped == 2
    assert len(notified) == 1
    assert {j.posting_id for j in notified[0]} == {"a", "b"}
    repo.close()


def test_second_cycle_finds_no_new_jobs(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs = [JobPosting(posting_id="a", title="SWE", source_adapter="12twenty")]
    _patch_browser_and_adapter(monkeypatch, jobs)

    repo = JobRepository(settings.db_path)
    notified: list[list[JobPosting]] = []
    sched = Scheduler(settings, repo, notified.append)

    sched._scrape_cycle()
    second = sched._scrape_cycle()

    assert second.new_count == 0
    assert second.updated_count == 1
    assert len(notified) == 1  # only the first cycle notified
    repo.close()


def test_dry_run_persists_but_does_not_notify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("PORTAL_USERNAME", "u")
    monkeypatch.setenv("PORTAL_PASSWORD", "p")
    monkeypatch.setenv("PORTAL_JOBS_URL", "https://example.com")
    settings = Settings(db_path=tmp_path / "jobs.db", dry_run=True)

    jobs = [JobPosting(posting_id="a", title="SWE", source_adapter="12twenty")]
    _patch_browser_and_adapter(monkeypatch, jobs)

    repo = JobRepository(settings.db_path)
    notified: list[list[JobPosting]] = []
    sched = Scheduler(settings, repo, notified.append)

    result = sched._scrape_cycle()

    assert result.new_count == 1
    assert notified == []  # dry run suppresses delivery
    assert repo.get_job("a") is not None
    repo.close()


def test_disappeared_posting_is_marked_closed(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # First cycle: two jobs present.
    _patch_browser_and_adapter(
        monkeypatch,
        [
            JobPosting(posting_id="a", title="SWE", source_adapter="12twenty"),
            JobPosting(posting_id="b", title="TA", source_adapter="12twenty"),
        ],
    )
    repo = JobRepository(settings.db_path)
    sched = Scheduler(settings, repo, lambda _jobs: None)
    sched._scrape_cycle()

    # Second cycle: "b" has vanished from the portal.
    _patch_browser_and_adapter(
        monkeypatch, [JobPosting(posting_id="a", title="SWE", source_adapter="12twenty")]
    )
    result = sched._scrape_cycle()

    assert result.closed_count == 1
    assert repo.get_job("b").status == ApplicationStatus.CLOSED
    assert repo.get_job("a").status != ApplicationStatus.CLOSED
    repo.close()


def test_keyword_filter_excludes_non_matching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("PORTAL_USERNAME", "u")
    monkeypatch.setenv("PORTAL_PASSWORD", "p")
    monkeypatch.setenv("PORTAL_JOBS_URL", "https://example.com")
    monkeypatch.setenv("KEYWORD_FILTERS", "engineer")
    settings = Settings(db_path=tmp_path / "jobs.db")

    _patch_browser_and_adapter(
        monkeypatch,
        [
            JobPosting(posting_id="a", title="Software Engineer", source_adapter="x"),
            JobPosting(posting_id="b", title="Barista", source_adapter="x"),
        ],
    )
    repo = JobRepository(settings.db_path)
    sched = Scheduler(settings, repo, lambda _jobs: None)
    result = sched._scrape_cycle()

    assert result.new_count == 1
    assert repo.get_job("a") is not None
    assert repo.get_job("b") is None
    repo.close()
