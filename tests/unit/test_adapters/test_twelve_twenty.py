"""
Tests for the 12twenty card parser.

A tiny fake of Playwright's ElementHandle replays the structure we verified
against the live UTD Student Employment DOM, so we can assert the field
extraction without a browser.
"""

from __future__ import annotations

from job_sentinel.adapters.sites.twelve_twenty import TwelveTwentyAdapter
from job_sentinel.config.settings import ScraperSettings


class _El:
    def __init__(self, text: str = "", attrs: dict | None = None) -> None:
        self._text = text
        self._attrs = attrs or {}

    def inner_text(self) -> str:
        return self._text

    def get_attribute(self, name: str) -> str | None:
        return self._attrs.get(name)


class _Card:
    """Maps the selectors the adapter uses to canned elements."""

    def __init__(self, single: dict, multi: dict | None = None) -> None:
        self._single = single
        self._multi = multi or {}

    def query_selector(self, selector: str):
        return self._single.get(selector)

    def query_selector_all(self, selector: str):
        return self._multi.get(selector, [])


class _Page:
    url = "https://utdallas.12twenty.com/jobPostings"


def _adapter() -> TwelveTwentyAdapter:
    return TwelveTwentyAdapter(ScraperSettings())


def _full_card() -> _Card:
    return _Card(
        single={
            "a.job-title": _El(attrs={"href": "/jobPostings#/jobPostings/35006705324740"}),
            "a.job-title .primary-item-text": _El("Student Affairs Student Assistant"),
            "span.sub-info:not(:has(span.sub-info-item))": _El("UT Dallas - Student Affairs"),
            "tt-date-time-display": _El("06/12/2026, 5:00pm CDT"),
        },
        multi={
            "span.sub-info-item": [
                _El("Richardson - TX"),
                _El("Part-Time Job"),
                _El("5 days ago"),
                _El("Apply By: 06/12/2026, 5:00pm CDT"),
            ]
        },
    )


def test_parses_all_fields() -> None:
    job = _adapter()._parse_card(_full_card(), _Page())
    assert job is not None
    assert job.posting_id == "35006705324740"
    assert job.title == "Student Affairs Student Assistant"
    assert job.employer == "UT Dallas - Student Affairs"
    assert job.location == "Richardson - TX"
    assert job.job_type == "Part-Time Job"
    assert job.posted_date == "5 days ago"
    assert job.deadline == "06/12/2026, 5:00pm CDT"
    assert job.portal_url.endswith("/jobPostings/35006705324740")
    assert job.source_adapter == "12twenty"


def test_apply_immediately_has_no_deadline() -> None:
    card = _Card(
        single={
            "a.job-title": _El(attrs={"href": "#/jobPostings/999"}),
            "a.job-title .primary-item-text": _El("Lifeguard"),
            "span.sub-info:not(:has(span.sub-info-item))": _El("UT Dallas - University Recreation"),
            "tt-date-time-display": None,
        },
        multi={
            "span.sub-info-item": [
                _El("Richardson - TX"),
                _El("Part-Time Job"),
                _El("3 weeks ago"),
                _El("Apply Immediately"),
            ]
        },
    )
    job = _adapter()._parse_card(card, _Page())
    assert job is not None
    assert job.posting_id == "999"
    assert job.location == "Richardson - TX"
    assert job.job_type == "Part-Time Job"
    assert job.posted_date == "3 weeks ago"
    assert job.deadline == ""


def test_row_without_posting_id_is_skipped() -> None:
    card = _Card(single={"a.job-title": _El(attrs={"href": "/jobPostings#/jobPostings/home"})})
    assert _adapter()._parse_card(card, _Page()) is None


def test_missing_title_link_is_skipped() -> None:
    assert _adapter()._parse_card(_Card(single={}), _Page()) is None


# ── URL hygiene ───────────────────────────────────────────────────────────────


def test_sanitize_strips_view_id() -> None:
    from job_sentinel.adapters.sites.twelve_twenty import sanitize_jobs_url

    url = "https://u.12twenty.com/jobPostings#/jobPostings/index?viewId=6&tab=studentEmployment"
    assert (
        sanitize_jobs_url(url)
        == "https://u.12twenty.com/jobPostings#/jobPostings/index?tab=studentEmployment"
    )


def test_sanitize_handles_trailing_view_id() -> None:
    from job_sentinel.adapters.sites.twelve_twenty import sanitize_jobs_url

    url = "https://u.12twenty.com/jobPostings#/jobPostings/index?tab=x&viewId=12"
    assert sanitize_jobs_url(url) == "https://u.12twenty.com/jobPostings#/jobPostings/index?tab=x"


def test_sanitize_leaves_clean_url_alone() -> None:
    from job_sentinel.adapters.sites.twelve_twenty import sanitize_jobs_url

    url = "https://u.12twenty.com/jobPostings#/jobPostings/index?tab=studentEmployment"
    assert sanitize_jobs_url(url) == url


# ── API item mapping (post-query JSON → JobPosting) ───────────────────────────

_API_ITEM = {
    "Id": 35006705360961,
    "TitleDisplay": "Rock Wall Staff",
    "JobTitle": "Rock Wall Staff",
    "CompanyName": "UT Dallas - University Recreation",
    "LocationDisplay": "Richardson - TX",
    "JobPostingJobTypeNames": "Part-Time Job",
    "PostedDate": "2026-06-11T19:38:31",
    "ApplicationDeadlineDate": "2026-08-17T13:00:00",
    "NumApplicants": 6,
    "ApplicationStatusDisplay": "Not Applied",
    "IsApplied": False,
    "StatusName": "Application Open",
    "CompanyId": 181499996802405,
}


def test_job_from_api_maps_fields() -> None:
    job = _adapter()._job_from_api(_API_ITEM)
    assert job is not None
    assert job.posting_id == "35006705360961"
    assert job.title == "Rock Wall Staff"
    assert job.employer == "UT Dallas - University Recreation"
    assert job.location == "Richardson - TX"
    assert job.job_type == "Part-Time Job"
    assert job.posted_date == "2026-06-11"
    assert job.deadline == "2026-08-17"
    assert job.portal_url.endswith("/jobPostings#/jobPostings/35006705360961")
    assert job.raw_data["num_applicants"] == 6


def test_job_from_api_missing_id_is_skipped() -> None:
    assert _adapter()._job_from_api({"TitleDisplay": "No id"}) is None


# ── Detail summarisation helpers ──────────────────────────────────────────────


def test_strip_html_flattens_rich_text() -> None:
    from job_sentinel.adapters.sites.twelve_twenty import _strip_html

    html = "<p>First line</p><p>Second &amp; third</p><ul><li>bullet</li></ul>"
    text = _strip_html(html)
    assert "First line" in text
    assert "Second & third" in text
    assert "<" not in text


def test_summarise_detail_curates_fields() -> None:
    from job_sentinel.adapters.sites.twelve_twenty import _summarise_detail

    detail = {
        "BaseSalary": 10.0,
        "CurrencyName": "USD",
        "PayFormatName": "per hour",
        "Industries": [{"Name": "Higher Education"}, {"Name": None}],
        "Functions": [{"Name": "Management"}],
        "IsWorkStudyRequired": False,
        "JobPostingApplicationDocumentTypes": [
            {"DocumentTypeName": "Resume", "IsRequired": True},
            {"DocumentTypeName": None, "IsRequired": False},
        ],
        "ContactName": "MacNeary J Siner",
        "ContactEmail": "mjs@utdallas.edu",
        "NumApplicants": 6,
    }
    summary = _summarise_detail(detail, "Job description text")
    assert summary["salary"] == "10.0 USD per hour"
    assert summary["industry"] == "Higher Education"
    assert summary["job_function"] == "Management"
    assert summary["application_documents"] == ["Resume (Required)"]
    assert summary["contact_name"] == "MacNeary J Siner"
    assert summary["description"] == "Job description text"


def test_join_names_skips_null_and_non_dicts() -> None:
    from job_sentinel.adapters.sites.twelve_twenty import _join_names

    assert _join_names([{"Name": "A"}, {"Name": None}, "junk", {"DisplayName": "B"}]) == "A, B"
    assert _join_names(None) == ""


# ── Session check ─────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, ok: bool, status: int = 200, body: dict | None = None) -> None:
        self.ok = ok
        self.status = status
        self._body = body or {}

    def json(self) -> dict:
        return self._body


class _FakeRequest:
    def __init__(self, response: _FakeResponse | Exception) -> None:
        self._response = response

    def get(self, url: str, timeout: int = 0) -> _FakeResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class _FakeContext:
    def __init__(self, response: _FakeResponse | Exception) -> None:
        self.request = _FakeRequest(response)


def test_check_session_valid_returns_user() -> None:
    ctx = _FakeContext(_FakeResponse(ok=True, body={"FullName": "Harshit Wandhare"}))
    status = _adapter().check_session(ctx)
    assert status.valid is True
    assert status.user == "Harshit Wandhare"


def test_check_session_unauthorized() -> None:
    status = _adapter().check_session(_FakeContext(_FakeResponse(ok=False, status=401)))
    assert status.valid is False
    assert "401" in status.detail


def test_check_session_network_error() -> None:
    status = _adapter().check_session(_FakeContext(ConnectionError("offline")))
    assert status.valid is False
    assert "offline" in status.detail
