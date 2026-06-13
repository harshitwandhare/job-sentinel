"""Tests for the The Muse source."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.sources.base import JobQuery
from job_sentinel.sources.themuse import TheMuseSource

_SAMPLE = {
    "results": [
        {
            "id": 1001,
            "name": "Data Engineer",
            "publication_date": "2026-06-05T00:00:00Z",
            "company": {"name": "Data Co"},
            "locations": [{"name": "New York, NY"}],
            "levels": [{"name": "Mid Level"}],
            "refs": {"landing_page": "https://themuse.com/jobs/1001"},
            "contents": "We need a data engineer with Python skills.",
        }
    ],
    "total": 1,
    "page": 0,
    "page_size": 20,
}


@respx.mock
def test_themuse_parses_job() -> None:
    respx.get("https://www.themuse.com/api/public/jobs").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    source = TheMuseSource()
    results = source.search(JobQuery(keywords="data"))

    assert len(results) == 1
    job = results[0]
    assert job.posting_id == "themuse:1001"
    assert job.title == "Data Engineer"
    assert job.employer == "Data Co"
    assert job.location == "New York, NY"
    assert job.job_type == "Mid Level"
    assert "themuse.com" in job.portal_url


@respx.mock
def test_themuse_no_results_returns_empty() -> None:
    respx.get("https://www.themuse.com/api/public/jobs").mock(
        return_value=httpx.Response(200, json={"results": [], "total": 0})
    )

    source = TheMuseSource()
    results = source.search(JobQuery())
    assert results == []


@respx.mock
def test_themuse_handles_http_error() -> None:
    respx.get("https://www.themuse.com/api/public/jobs").mock(return_value=httpx.Response(429))

    source = TheMuseSource()
    assert source.search(JobQuery()) == []


@respx.mock
def test_themuse_keyword_filter() -> None:
    """Jobs not matching the keyword should be excluded."""
    respx.get("https://www.themuse.com/api/public/jobs").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    source = TheMuseSource()
    results = source.search(JobQuery(keywords="design"))
    assert results == []
