"""Tests for the USAJobs source — auth headers and response parsing."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.sources.base import JobQuery
from job_sentinel.sources.usajobs import USAJobsSource

_SAMPLE = {
    "SearchResult": {
        "SearchResultItems": [
            {
                "MatchedObjectDescriptor": {
                    "PositionID": "USAJOB-001",
                    "PositionTitle": "IT Specialist",
                    "OrganizationName": "Dept of Labor",
                    "PositionLocation": [{"LocationName": "Washington, DC"}],
                    "PositionStartDate": "2026-06-01",
                    "ApplyURI": ["https://usajobs.gov/job/001/apply"],
                    "PositionRemuneration": [
                        {
                            "MinimumRange": "80000",
                            "MaximumRange": "110000",
                            "RateIntervalCode": "PA",
                        }
                    ],
                    "PositionSchedule": [{"Name": "Full-Time"}],
                    "UserArea": {"Details": {"JobSummary": "IT support for federal agency."}},
                }
            }
        ]
    }
}


@respx.mock
def test_usajobs_includes_auth_headers() -> None:
    route = respx.get("https://data.usajobs.gov/api/search").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    source = USAJobsSource(api_key="mykey", email="test@example.com")
    source.search(JobQuery(keywords="IT"))

    assert route.called
    req = route.calls[0].request
    assert req.headers.get("Authorization-Key") == "mykey"
    assert req.headers.get("User-Agent") == "test@example.com"


@respx.mock
def test_usajobs_parses_job() -> None:
    respx.get("https://data.usajobs.gov/api/search").mock(
        return_value=httpx.Response(200, json=_SAMPLE)
    )

    source = USAJobsSource(api_key="k", email="e@x.com")
    results = source.search(JobQuery())

    assert len(results) == 1
    job = results[0]
    assert job.posting_id == "usajobs:USAJOB-001"
    assert job.title == "IT Specialist"
    assert job.employer == "Dept of Labor"
    assert job.location == "Washington, DC"
    assert "80000" in job.raw_data.get("salary_text", "")


def test_usajobs_not_configured_returns_empty() -> None:
    source = USAJobsSource()
    assert source.configured() is False
    assert source.search(JobQuery()) == []


@respx.mock
def test_usajobs_handles_error() -> None:
    respx.get("https://data.usajobs.gov/api/search").mock(return_value=httpx.Response(403))

    assert USAJobsSource(api_key="k", email="e@x.com").search(JobQuery()) == []
