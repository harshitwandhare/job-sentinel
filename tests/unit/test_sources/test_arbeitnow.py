"""Tests for the Arbeitnow source."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.sources.arbeitnow import ArbeitnowSource
from job_sentinel.sources.base import JobQuery

_SAMPLE = {
    "data": [
        {
            "slug": "python-dev-acme",
            "title": "Python Developer",
            "company_name": "Acme EU",
            "location": "Berlin, Germany",
            "job_types": ["full_time"],
            "remote": True,
            "visa_sponsorship": False,
            "created_at": 1717200000,
            "url": "https://www.arbeitnow.com/jobs/python-dev-acme",
            "description": "Build microservices with Python.",
            "tags": ["python", "microservices"],
        }
    ]
}


@respx.mock
def test_arbeitnow_parses_job() -> None:
    respx.get("https://www.arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    source = ArbeitnowSource()
    results = source.search(JobQuery(keywords="python"))

    assert len(results) == 1
    job = results[0]
    assert job.posting_id == "arbeitnow:python-dev-acme"
    assert job.title == "Python Developer"
    assert job.employer == "Acme EU"
    assert job.raw_data.get("is_remote") is True
    assert job.raw_data.get("visa_sponsorship") is False


@respx.mock
def test_arbeitnow_remote_filter_passed() -> None:
    """When remote=True is set, the param should be forwarded."""
    route = respx.get("https://www.arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    source = ArbeitnowSource()
    source.search(JobQuery(remote=True))

    assert route.called
    req = route.calls[0].request
    assert "remote=true" in str(req.url)


@respx.mock
def test_arbeitnow_handles_error() -> None:
    respx.get("https://www.arbeitnow.com/api/job-board-api").mock(return_value=httpx.Response(503))

    assert ArbeitnowSource().search(JobQuery()) == []
