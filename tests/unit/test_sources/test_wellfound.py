"""Tests for the Wellfound source."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.sources.base import JobQuery
from job_sentinel.sources.wellfound import WellfoundSource

_GQL_URL = "https://wellfound.com/graphql"

_SAMPLE_RESP = {
    "data": {
        "jobListings": {
            "startups": [
                {
                    "name": "Acme Corp",
                    "jobListings": [
                        {
                            "id": "wf-001",
                            "title": "Senior Backend Engineer",
                            "description": "Build distributed systems at scale.",
                            "jobType": "full_time",
                            "remote": True,
                            "salary": "$140k–$180k",
                            "createdAt": "2026-06-14",
                            "slug": "acme-corp-senior-backend",
                            "startupRole": {"url": "https://wellfound.com/jobs/wf-001"},
                        }
                    ],
                }
            ]
        }
    }
}


@respx.mock
def test_wellfound_parses_job() -> None:
    respx.post(_GQL_URL).mock(return_value=httpx.Response(200, json=_SAMPLE_RESP))

    source = WellfoundSource()
    results = source.search(JobQuery(keywords="backend"))

    assert len(results) == 1
    job = results[0]
    assert job.posting_id == "wellfound:wf-001"
    assert job.title == "Senior Backend Engineer"
    assert job.employer == "Acme Corp"
    assert job.raw_data.get("is_remote") is True
    assert "$140k" in job.raw_data.get("salary_text", "")


@respx.mock
def test_wellfound_empty_response() -> None:
    empty = {"data": {"jobListings": {"startups": []}}}
    respx.post(_GQL_URL).mock(return_value=httpx.Response(200, json=empty))

    assert WellfoundSource().search(JobQuery()) == []


@respx.mock
def test_wellfound_graphql_error_returns_empty() -> None:
    err = {"errors": [{"message": "Not authorized"}]}
    respx.post(_GQL_URL).mock(return_value=httpx.Response(200, json=err))

    assert WellfoundSource().search(JobQuery()) == []


@respx.mock
def test_wellfound_http_error_returns_empty() -> None:
    respx.post(_GQL_URL).mock(return_value=httpx.Response(503))

    assert WellfoundSource().search(JobQuery()) == []


@respx.mock
def test_wellfound_limit_respected() -> None:
    many_listings = [{"id": f"wf-{i}", "title": f"Role {i}", "remote": False} for i in range(20)]
    resp = {
        "data": {"jobListings": {"startups": [{"name": "BigCo", "jobListings": many_listings}]}}
    }
    respx.post(_GQL_URL).mock(return_value=httpx.Response(200, json=resp))

    results = WellfoundSource().search(JobQuery(limit=5))
    assert len(results) == 5
