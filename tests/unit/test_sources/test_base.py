"""
Tests for sources/base.py — JobQuery, SourceError, and JobSource._posting helper.
"""

from __future__ import annotations

from job_sentinel.core.models import ApplicationStatus
from job_sentinel.sources.base import JobPosting, JobQuery, JobSource, SourceError


class _Dummy(JobSource):
    SOURCE_ID = "dummy"
    LABEL = "Dummy"

    def search(self, query: JobQuery) -> list[JobPosting]:
        return []


def test_job_query_defaults() -> None:
    q = JobQuery()
    assert q.keywords == ""
    assert q.limit == 50
    assert q.remote is None


def test_job_query_fields() -> None:
    q = JobQuery(keywords="python", location="NYC", remote=True, limit=10)
    assert q.keywords == "python"
    assert q.remote is True
    assert q.limit == 10


def test_source_error_model() -> None:
    err = SourceError(source="remoteok", detail="timeout")
    assert err.source == "remoteok"
    assert "timeout" in err.detail


def test_posting_helper_sets_source_id() -> None:
    src = _Dummy()
    job = src._posting(
        native_id="abc123",
        title="Engineer",
        employer="Acme",
        apply_url="https://example.com/job/1",
    )
    assert job.posting_id == "dummy:abc123"
    assert job.source_adapter == "dummy"
    assert job.portal_url == "https://example.com/job/1"
    assert job.status == ApplicationStatus.NEW


def test_posting_helper_salary_and_remote_in_raw_data() -> None:
    src = _Dummy()
    job = src._posting(
        native_id="x",
        title="Dev",
        employer="Corp",
        salary_text="$120k",
        is_remote=True,
        tags=["python", "fastapi"],
    )
    assert job.raw_data["salary_text"] == "$120k"
    assert job.raw_data["is_remote"] is True
    assert "python" in job.raw_data["tags"]


def test_posting_helper_strips_long_description() -> None:
    src = _Dummy()
    long_desc = "x" * 400
    job = src._posting(native_id="y", title="T", employer="E", description_snippet=long_desc)
    # JobPosting.description_snippet truncates at 350 with ellipsis
    assert len(job.description_snippet) <= 355


def test_posting_helper_generates_id_when_native_id_empty() -> None:
    src = _Dummy()
    job = src._posting(native_id="", title="T", employer="E")
    assert job.posting_id.startswith("dummy:")
    assert len(job.posting_id) > len("dummy:")


def test_source_configured_default_true() -> None:
    assert _Dummy().configured() is True


def test_source_health_check_default_true() -> None:
    assert _Dummy().health_check() is True
