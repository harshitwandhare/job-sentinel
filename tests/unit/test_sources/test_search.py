"""
Tests for aggregate_search:
  - Deduplication by (title, employer) and by portal_url
  - Per-source error isolation (one failing source does not kill others)
  - Limit cap
  - Concurrency path (all sources run)
  - Sort newest-first
"""

from __future__ import annotations

from job_sentinel.core.models import JobPosting
from job_sentinel.sources.base import JobQuery, JobSource
from job_sentinel.sources.search import aggregate_search


def _make_job(
    title: str = "Dev",
    employer: str = "Corp",
    url: str = "",
    posted: str = "",
) -> JobPosting:
    from job_sentinel.core.models import ApplicationStatus

    return JobPosting(
        posting_id=f"test:{title}:{employer}",
        title=title,
        employer=employer,
        portal_url=url,
        status=ApplicationStatus.NEW,
        posted_date=posted,
        source_adapter="test",
    )


class _FixedSource(JobSource):
    SOURCE_ID = "fixed"
    LABEL = "Fixed"

    def __init__(self, jobs: list[JobPosting]) -> None:
        self._jobs = jobs

    def search(self, query: JobQuery) -> list[JobPosting]:
        return self._jobs


class _BrokenSource(JobSource):
    SOURCE_ID = "broken"
    LABEL = "Broken"

    def search(self, query: JobQuery) -> list[JobPosting]:
        msg = "network timeout"
        raise RuntimeError(msg)


def test_aggregate_returns_results_from_all_sources() -> None:
    jobs_a = [_make_job("SWE", "A")]
    jobs_b = [_make_job("PM", "B")]

    src_a = _FixedSource(jobs_a)
    src_a.SOURCE_ID = "src_a"
    src_b = _FixedSource(jobs_b)
    src_b.SOURCE_ID = "src_b"

    resp = aggregate_search(JobQuery(limit=50), [src_a, src_b])

    assert len(resp.results) == 2
    assert resp.errors == []
    assert resp.counts["src_a"] == 1
    assert resp.counts["src_b"] == 1


def test_broken_source_captured_in_errors() -> None:
    good = _FixedSource([_make_job("Dev", "GoodCo")])
    good.SOURCE_ID = "good"
    bad = _BrokenSource()

    resp = aggregate_search(JobQuery(limit=50), [good, bad])

    titles = [j.title for j in resp.results]
    assert "Dev" in titles
    assert len(resp.errors) == 1
    assert resp.errors[0].source == "broken"
    assert "timeout" in resp.errors[0].detail


def test_deduplication_by_title_employer() -> None:
    """Same (title, employer) from two sources → kept only once."""
    job1 = _make_job("Python Dev", "Acme")
    job2 = _make_job("Python Dev", "Acme")  # duplicate
    job3 = _make_job("Go Dev", "Acme")

    src = _FixedSource([job1, job2, job3])
    src.SOURCE_ID = "dup_test"

    resp = aggregate_search(JobQuery(limit=50), [src])

    assert len(resp.results) == 2  # dup dropped


def test_deduplication_by_url() -> None:
    """Same portal_url from two sources → kept only once."""
    job1 = _make_job("Dev A", "Co1", url="https://example.com/job/1")
    job2 = _make_job("Dev B", "Co2", url="https://example.com/job/1")  # same URL

    src = _FixedSource([job1, job2])
    src.SOURCE_ID = "url_dup"

    resp = aggregate_search(JobQuery(limit=50), [src])
    assert len(resp.results) == 1


def test_limit_cap() -> None:
    many = [_make_job(f"Job {i}", f"Co {i}") for i in range(30)]
    src = _FixedSource(many)
    src.SOURCE_ID = "limit_src"

    resp = aggregate_search(JobQuery(limit=10), [src])
    assert len(resp.results) == 10


def test_sort_newest_first() -> None:
    old = _make_job("Old Job", "Co", posted="2026-01-01")
    new = _make_job("New Job", "Co", posted="2026-06-10")
    mid = _make_job("Mid Job", "Co", posted="2026-03-15")

    src = _FixedSource([old, new, mid])
    src.SOURCE_ID = "sort_src"

    resp = aggregate_search(JobQuery(limit=50), [src])
    dates = [j.posted_date for j in resp.results]
    assert dates[0] == "2026-06-10"
    assert dates[-1] == "2026-01-01"


def test_empty_sources_list_returns_empty_response() -> None:
    resp = aggregate_search(JobQuery(), [])
    assert resp.results == []
    assert resp.errors == []
    assert resp.counts == {}
