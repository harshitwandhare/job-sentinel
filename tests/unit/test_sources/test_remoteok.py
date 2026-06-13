"""Tests for the Remote OK source — HTTP mocked with respx."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.sources.base import JobQuery
from job_sentinel.sources.remoteok import RemoteOkSource

_SAMPLE = [
    {"Legal": "no scraping"},  # metadata element (skipped)
    {
        "id": 99,
        "slug": "senior-python-engineer-at-acme",
        "position": "Senior Python Engineer",
        "company": "Acme Corp",
        "location": "Worldwide",
        "date": "2026-06-01T00:00:00Z",
        "url": "https://remoteok.com/l/99",
        "apply_url": "https://acme.com/apply",
        "description": "We need a Python expert.",
        "salary": "$130k–$160k",
        "tags": ["python", "fastapi"],
    },
    {
        "id": 100,
        "position": "React Developer",
        "company": "Beta Inc",
        "location": "Worldwide",
        "date": "2026-05-30T00:00:00Z",
        "url": "https://remoteok.com/l/100",
        "apply_url": "https://betainc.com/jobs",
        "description": "React frontend dev needed.",
        "salary": "",
        "tags": ["react"],
    },
]


@respx.mock
def test_remoteok_parses_jobs() -> None:
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=_SAMPLE))

    source = RemoteOkSource()
    results = source.search(JobQuery(keywords="python"))

    # Only the Python job matches the keyword filter
    assert len(results) == 1
    job = results[0]
    assert job.posting_id == "remoteok:99"
    assert job.title == "Senior Python Engineer"
    assert job.employer == "Acme Corp"
    assert job.portal_url == "https://acme.com/apply"
    assert job.raw_data.get("salary_text") == "$130k–$160k"
    assert job.raw_data.get("is_remote") is True
    assert "python" in job.raw_data.get("tags", [])


@respx.mock
def test_remoteok_no_keyword_returns_all() -> None:
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=_SAMPLE))

    source = RemoteOkSource()
    results = source.search(JobQuery(keywords=""))
    assert len(results) == 2


@respx.mock
def test_remoteok_handles_http_error_gracefully() -> None:
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(500))

    source = RemoteOkSource()
    results = source.search(JobQuery())
    assert results == []


@respx.mock
def test_remoteok_handles_invalid_json() -> None:
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(200, content=b"not json")
    )

    source = RemoteOkSource()
    results = source.search(JobQuery())
    assert results == []


@respx.mock
def test_remoteok_respects_limit() -> None:
    many = [{"Legal": "meta"}] + [
        {
            "id": i,
            "position": f"Job {i}",
            "company": "Co",
            "location": "Worldwide",
            "url": f"https://remoteok.com/{i}",
            "apply_url": f"https://co.com/{i}",
            "description": "desc",
            "date": "",
            "salary": "",
            "tags": [],
        }
        for i in range(20)
    ]
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=many))

    source = RemoteOkSource()
    results = source.search(JobQuery(limit=5))
    assert len(results) == 5
