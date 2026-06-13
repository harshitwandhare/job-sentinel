"""Tests for the Himalayas source."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.sources.base import JobQuery
from job_sentinel.sources.himalayas import HimalayasSource

_SAMPLE = {
    "jobs": [
        {
            "id": "him-001",
            "title": "Backend Engineer",
            "company": {"name": "Remote Startup"},
            "jobType": "full_time",
            "createdAt": "2026-06-10",
            "applicationLink": "https://himalayas.app/jobs/him-001/apply",
            "description": "Build scalable backends.",
            "salaryMin": 90000,
            "salaryMax": 130000,
            "currency": "USD",
        }
    ]
}


@respx.mock
def test_himalayas_parses_job() -> None:
    respx.get("https://himalayas.app/jobs/api/search").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    source = HimalayasSource()
    results = source.search(JobQuery())

    assert len(results) == 1
    job = results[0]
    assert job.posting_id == "himalayas:him-001"
    assert job.title == "Backend Engineer"
    assert job.employer == "Remote Startup"
    assert job.raw_data.get("is_remote") is True
    assert "90,000" in job.raw_data.get("salary_text", "")


@respx.mock
def test_himalayas_missing_fields_handled() -> None:
    minimal = {"jobs": [{"id": "x1", "title": "Dev"}]}
    respx.get("https://himalayas.app/jobs/api/search").mock(
        return_value=httpx.Response(200, json=minimal)
    )

    source = HimalayasSource()
    results = source.search(JobQuery())
    assert len(results) == 1
    assert results[0].employer == ""


@respx.mock
def test_himalayas_handles_error() -> None:
    respx.get("https://himalayas.app/jobs/api/search").mock(return_value=httpx.Response(500))

    assert HimalayasSource().search(JobQuery()) == []
