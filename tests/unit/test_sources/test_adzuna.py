"""Tests for the Adzuna source — auth params and response parsing."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.sources.adzuna import AdzunaSource
from job_sentinel.sources.base import JobQuery

_SAMPLE = {
    "results": [
        {
            "id": "adzuna-7654",
            "title": "Software Engineer",
            "company": {"display_name": "BigTech"},
            "location": {"area": ["US", "California", "San Francisco"]},
            "contract_type": "permanent",
            "created": "2026-06-08T12:00:00Z",
            "redirect_url": "https://adzuna.com/jobs/7654",
            "description": "Join our engineering team.",
            "salary_min": 120000.0,
            "salary_max": 160000.0,
        }
    ]
}


@respx.mock
def test_adzuna_includes_auth_params() -> None:
    route = respx.get("https://api.adzuna.com/v1/api/jobs/us/search/1").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    source = AdzunaSource(app_id="myid", app_key="mykey", country="us")
    source.search(JobQuery(keywords="python"))

    assert route.called
    url = str(route.calls[0].request.url)
    assert "app_id=myid" in url
    assert "app_key=mykey" in url
    assert "what=python" in url


@respx.mock
def test_adzuna_parses_job_correctly() -> None:
    respx.get("https://api.adzuna.com/v1/api/jobs/us/search/1").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    source = AdzunaSource(app_id="id", app_key="key")
    results = source.search(JobQuery())

    assert len(results) == 1
    job = results[0]
    assert job.posting_id == "adzuna:adzuna-7654"
    assert job.title == "Software Engineer"
    assert job.employer == "BigTech"
    assert "$120,000" in job.raw_data.get("salary_text", "")


def test_adzuna_not_configured_returns_empty() -> None:
    source = AdzunaSource()
    assert source.configured() is False
    results = source.search(JobQuery())
    assert results == []


@respx.mock
def test_adzuna_forwards_salary_min() -> None:
    route = respx.get("https://api.adzuna.com/v1/api/jobs/us/search/1").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    AdzunaSource(app_id="x", app_key="y").search(JobQuery(salary_min=80000))

    url = str(route.calls[0].request.url)
    assert "salary_min=80000" in url


@respx.mock
def test_adzuna_handles_http_error() -> None:
    respx.get("https://api.adzuna.com/v1/api/jobs/us/search/1").mock(
        return_value=httpx.Response(401)
    )

    assert AdzunaSource(app_id="x", app_key="y").search(JobQuery()) == []
