"""
Tests for the JobSpy scraper source.

python-jobspy is NOT installed in the dev env (it's an optional extra).
These tests verify:
  1. ImportError → helpful RuntimeError with install instructions.
  2. When monkeypatched, the source maps DataFrame rows to JobPosting.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from job_sentinel.sources.base import JobQuery
from job_sentinel.sources.jobspy_source import TOS_WARNING, JobSpySource


def test_tos_warning_present() -> None:
    assert "LinkedIn" in TOS_WARNING
    assert "hiQ" in TOS_WARNING


def test_import_error_raises_helpful_message() -> None:
    """When jobspy is not installed, search() raises a RuntimeError with install hint."""
    source = JobSpySource()

    # Patch sys.modules so the import inside search() fails
    with (
        patch.dict(sys.modules, {"jobspy": None}),
        pytest.raises(RuntimeError, match="pip install job-sentinel\\[sources\\]"),
    ):
        source.search(JobQuery(keywords="python"))


def test_search_maps_dataframe_rows() -> None:
    """When jobspy is installed (mocked), rows are mapped to JobPosting."""
    # Build a lightweight iterable that quacks like a DataFrame for iterrows()
    row = {
        "id": "idx-1",
        "title": "Python Dev",
        "company": "TechCorp",
        "location": "Remote",
        "job_type": "fulltime",
        "date_posted": "2026-06-10",
        "job_url": "https://indeed.com/job/1",
        "description": "Build Python services.",
        "min_amount": 100000.0,
        "max_amount": 140000.0,
        "currency": "USD",
        "interval": "yearly",
        "is_remote": True,
        "site": "indeed",
    }

    # Simulate what df.iterrows() produces: iterable of (index, mapping) pairs
    mock_df = MagicMock()
    mock_df.iterrows.return_value = iter([(0, row)])

    mock_jobspy = MagicMock()
    mock_jobspy.scrape_jobs.return_value = mock_df

    with patch.dict(sys.modules, {"jobspy": mock_jobspy}):
        source = JobSpySource()
        results = source.search(JobQuery(keywords="python"))

    assert len(results) == 1
    job = results[0]
    assert job.title == "Python Dev"
    assert job.employer == "TechCorp"
    assert job.raw_data.get("is_remote") is True
    assert "100,000" in job.raw_data.get("salary_text", "")
    assert job.portal_url == "https://indeed.com/job/1"


def test_search_handles_scrape_exception() -> None:
    """If scrape_jobs raises, search() returns [] without propagating."""
    mock_jobspy = MagicMock()
    mock_jobspy.scrape_jobs.side_effect = RuntimeError("site down")

    with patch.dict(sys.modules, {"jobspy": mock_jobspy}):
        source = JobSpySource()
        results = source.search(JobQuery())

    assert results == []
