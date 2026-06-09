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
