"""Tests for the find / screen / queue pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from job_sentinel.core.eligibility import Status, Verdict
from job_sentinel.core.models import Application, ApplicationStage, JobPosting
from job_sentinel.core.pipeline import Screened, queue_jobs, run_find, screen_jobs
from job_sentinel.db.repository import JobRepository

if TYPE_CHECKING:
    from pathlib import Path


def posting(pid: str, url: str = "", employer: str = "Acme") -> JobPosting:
    # Titles differ per id: aggregate_search deduplicates on (title, employer),
    # so identical titles would collapse before the pipeline sees them.
    return JobPosting(
        posting_id=pid,
        title=f"Software Engineer Intern {pid}",
        employer=employer,
        portal_url=url,
        source_adapter="simplify",
    )


@pytest.fixture
def repo(tmp_path: Path) -> JobRepository:
    return JobRepository(tmp_path / "jobs.db")


# ── screening ─────────────────────────────────────────────────────────────────


def test_a_posting_without_a_url_is_kept_not_dropped() -> None:
    """A missing link is not evidence of an exclusion."""
    out = screen_jobs([posting("1")])
    assert len(out) == 1
    assert out[0].verdict.status is Status.UNKNOWN
    assert out[0].eligible


def test_an_unreadable_posting_counts_as_eligible() -> None:
    """A board that times out must not quietly hide the role."""
    item = Screened(posting("1"), Verdict(Status.UNKNOWN, detail="timeout"))
    assert item.eligible


def test_a_blocked_posting_is_not_eligible() -> None:
    item = Screened(posting("1"), Verdict(Status.BLOCKED, blockers=[("no sponsorship", "...")]))
    assert not item.eligible


# ── queueing ──────────────────────────────────────────────────────────────────


def test_queues_eligible_postings_as_saved_applications(repo: JobRepository) -> None:
    items = [Screened(posting("1", "https://x.test/1"), Verdict(Status.ELIGIBLE))]
    queued, duplicates = queue_jobs(items, repo)
    assert duplicates == 0
    assert [a.stage for a in queued] == [ApplicationStage.SAVED]
    assert repo.list_applications()[0].url == "https://x.test/1"


def test_the_verdict_is_kept_on_the_application(repo: JobRepository) -> None:
    """A wrong screen has to be visible later, not silent."""
    verdict = Verdict(Status.ELIGIBLE, cautions=[("export control", "quote")])
    queued, _ = queue_jobs([Screened(posting("1", "https://x.test/1"), verdict)], repo)
    assert queued[0].raw_data["eligibility"]["cautions"] == ["export control"]
    assert "export control" in queued[0].notes


def test_a_url_already_tracked_is_not_queued_again(repo: JobRepository) -> None:
    repo.create_application(Application(url="https://x.test/1", stage=ApplicationStage.REJECTED))
    items = [Screened(posting("1", "https://x.test/1"), Verdict(Status.ELIGIBLE))]
    queued, duplicates = queue_jobs(items, repo)
    assert queued == []
    assert duplicates == 1


def test_deduplication_ignores_case(repo: JobRepository) -> None:
    repo.create_application(Application(url="https://X.TEST/1"))
    items = [Screened(posting("1", "https://x.test/1"), Verdict(Status.ELIGIBLE))]
    _, duplicates = queue_jobs(items, repo)
    assert duplicates == 1


def test_two_postings_with_the_same_url_in_one_run_queue_once(repo: JobRepository) -> None:
    """Aggregated sources repeat roles; the second copy is a duplicate."""
    items = [
        Screened(posting("1", "https://x.test/1"), Verdict(Status.ELIGIBLE)),
        Screened(posting("2", "https://x.test/1"), Verdict(Status.ELIGIBLE)),
    ]
    queued, duplicates = queue_jobs(items, repo)
    assert len(queued) == 1
    assert duplicates == 1


def test_postings_without_a_url_are_all_queued(repo: JobRepository) -> None:
    """An empty URL is not a shared identity."""
    items = [
        Screened(posting("1"), Verdict(Status.ELIGIBLE)),
        Screened(posting("2"), Verdict(Status.ELIGIBLE)),
    ]
    queued, duplicates = queue_jobs(items, repo)
    assert len(queued) == 2
    assert duplicates == 0


# ── the whole pass ────────────────────────────────────────────────────────────


class _Source:
    SOURCE_ID = "fake"

    def __init__(self, results: list[JobPosting]) -> None:
        self._results = results

    def search(self, query: object) -> list[JobPosting]:
        return self._results


def test_run_find_without_screening_queues_everything(repo: JobRepository, tmp_path: Path) -> None:
    from job_sentinel.sources.base import JobQuery

    source = _Source([posting("1", "https://x.test/1"), posting("2", "https://x.test/2")])
    report = run_find(JobQuery(), object(), repo, sources=[source], screen=False)  # type: ignore[arg-type]
    assert report.found == 2
    assert report.screened == 0
    assert len(report.queued) == 2
    assert "2 found" in report.summary


def test_run_find_drops_blocked_postings(
    repo: JobRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    from job_sentinel.core import pipeline
    from job_sentinel.sources.base import JobQuery

    def fake_screen(url: str, *, timeout: float = 30.0) -> Verdict:
        if url.endswith("/2"):
            return Verdict(Status.BLOCKED, blockers=[("no sponsorship", "we do not sponsor")])
        return Verdict(Status.ELIGIBLE)

    monkeypatch.setattr(pipeline, "screen_url", fake_screen)
    source = _Source([posting("1", "https://x.test/1"), posting("2", "https://x.test/2")])
    report = run_find(JobQuery(), object(), repo, sources=[source])  # type: ignore[arg-type]

    assert [a.url for a in report.queued] == ["https://x.test/1"]
    assert len(report.blocked) == 1
    assert report.blocked[0].verdict.blockers[0][1] == "we do not sponsor"


# ── a run moving on ───────────────────────────────────────────────────────────


def test_next_to_fill_returns_something_unfilled(repo: JobRepository) -> None:
    from job_sentinel.core.pipeline import is_filled, next_to_fill

    items = [
        Screened(posting("1", "https://x.test/1"), Verdict(Status.ELIGIBLE)),
        Screened(posting("2", "https://x.test/2"), Verdict(Status.ELIGIBLE)),
    ]
    queue_jobs(items, repo)
    first = next_to_fill(repo)
    assert first is not None
    assert not is_filled(first)


def test_marking_filled_moves_the_run_on_without_claiming_an_application(
    repo: JobRepository,
) -> None:
    """The stage must stay saved: nothing has been submitted, and recording an
    application the user never sent is worse than useless."""
    from job_sentinel.core.pipeline import is_filled, mark_filled, next_to_fill

    queue_jobs(
        [
            Screened(posting("1", "https://x.test/1"), Verdict(Status.ELIGIBLE)),
            Screened(posting("2", "https://x.test/2"), Verdict(Status.ELIGIBLE)),
        ],
        repo,
    )
    first = next_to_fill(repo)
    assert first is not None

    updated = mark_filled(first.id, repo)
    assert updated is not None
    assert updated.stage is ApplicationStage.SAVED
    assert is_filled(updated)

    second = next_to_fill(repo)
    assert second is not None
    assert second.id != first.id


def test_marking_filled_keeps_the_eligibility_record(repo: JobRepository) -> None:
    from job_sentinel.core.pipeline import mark_filled

    verdict = Verdict(Status.ELIGIBLE, cautions=[("export control", "quote")])
    queued, _ = queue_jobs([Screened(posting("1", "https://x.test/1"), verdict)], repo)
    updated = mark_filled(queued[0].id, repo)
    assert updated is not None
    assert updated.raw_data["eligibility"]["cautions"] == ["export control"]


def test_marking_an_unknown_application_returns_none(repo: JobRepository) -> None:
    from job_sentinel.core.pipeline import mark_filled

    assert mark_filled("nope", repo) is None


def test_next_to_fill_is_none_when_everything_is_filled(repo: JobRepository) -> None:
    from job_sentinel.core.pipeline import mark_filled, next_to_fill

    queued, _ = queue_jobs(
        [Screened(posting("1", "https://x.test/1"), Verdict(Status.ELIGIBLE))], repo
    )
    mark_filled(queued[0].id, repo)
    assert next_to_fill(repo) is None
