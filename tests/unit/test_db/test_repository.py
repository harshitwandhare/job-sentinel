"""Tests for the SQLite repository layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from job_sentinel.core.models import ApplicationStatus, JobPosting
from job_sentinel.db.repository import JobRepository

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repo(tmp_path: Path) -> JobRepository:
    """A fresh in-memory-like repository per test (uses tmp_path)."""
    db = JobRepository(tmp_path / "test_jobs.db")
    yield db
    db.close()


def _make_job(pid: str = "test-001", **kwargs) -> JobPosting:
    return JobPosting(
        posting_id=pid,
        title="Software Engineer Intern",
        employer="Google",
        location="Dallas, TX",
        job_type="Internship",
        **kwargs,
    )


class TestSaveJob:
    def test_insert_returns_true(self, repo: JobRepository) -> None:
        job = _make_job()
        assert repo.save_job(job) is True

    def test_update_returns_false(self, repo: JobRepository) -> None:
        job = _make_job()
        repo.save_job(job)
        assert repo.save_job(job) is False

    def test_preserves_applied_status_on_re_scrape(self, repo: JobRepository) -> None:
        job = _make_job()
        repo.save_job(job)
        repo.update_status(job.posting_id, ApplicationStatus.APPLIED)

        # Simulate rescrape with same posting
        repo.save_job(job)
        fetched = repo.get_job(job.posting_id)
        assert fetched.status == ApplicationStatus.APPLIED


class TestGetJob:
    def test_returns_none_for_unknown(self, repo: JobRepository) -> None:
        assert repo.get_job("does-not-exist") is None

    def test_roundtrip(self, repo: JobRepository) -> None:
        job = _make_job(pid="roundtrip-01")
        repo.save_job(job)
        fetched = repo.get_job("roundtrip-01")
        assert fetched is not None
        assert fetched.title == job.title
        assert fetched.employer == job.employer


class TestUpdateStatus:
    def test_update_returns_true(self, repo: JobRepository) -> None:
        repo.save_job(_make_job())
        assert repo.update_status("test-001", ApplicationStatus.APPLIED) is True

    def test_update_unknown_returns_false(self, repo: JobRepository) -> None:
        assert repo.update_status("no-such-id", ApplicationStatus.APPLIED) is False


class TestStats:
    def test_counts_by_status(self, repo: JobRepository) -> None:
        repo.save_job(_make_job("j1"))
        repo.save_job(_make_job("j2"))
        repo.update_status("j1", ApplicationStatus.APPLIED)

        stats = repo.get_stats()
        assert stats["new"] == 1
        assert stats["applied"] == 1
        assert stats["total"] == 2


class TestExists:
    def test_exists_after_insert(self, repo: JobRepository) -> None:
        repo.save_job(_make_job())
        assert repo.exists("test-001") is True

    def test_not_exists_before_insert(self, repo: JobRepository) -> None:
        assert repo.exists("ghost") is False
