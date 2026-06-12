"""Tests for the Handshake adapter's card parsing and pagination."""

from __future__ import annotations

from job_sentinel.adapters.sites.handshake import (
    SEL_EMPLOYER,
    SEL_JOB_CARD,
    SEL_LOCATION,
    SEL_NEXT_PAGE,
    SEL_TITLE,
    HandshakeAdapter,
)
from job_sentinel.config.settings import ScraperSettings


class _El:
    def __init__(self, text: str = "", attrs: dict | None = None, enabled: bool = True) -> None:
        self._text = text
        self._attrs = attrs or {}
        self._enabled = enabled
        self.clicked = False

    def inner_text(self) -> str:
        return self._text

    def get_attribute(self, name: str) -> str | None:
        return self._attrs.get(name)

    def is_enabled(self) -> bool:
        return self._enabled

    def click(self) -> None:
        self.clicked = True


class _Card:
    def __init__(self, href: str, title: str, employer: str, location: str) -> None:
        self._map = {
            "a": _El(attrs={"href": href}),
            SEL_TITLE: _El(title),
            SEL_EMPLOYER: _El(employer),
            SEL_LOCATION: _El(location),
        }

    def query_selector(self, selector: str):
        return self._map.get(selector)


class _Page:
    def __init__(self, cards: list[_Card], next_btn: _El | None = None) -> None:
        self._cards = cards
        self._next = next_btn
        self.url = "https://app.joinhandshake.com/stu/postings"

    def wait_for_selector(self, selector: str, timeout: int = 0) -> None:
        pass

    def query_selector_all(self, selector: str):
        return self._cards if selector == SEL_JOB_CARD else []

    def query_selector(self, selector: str):
        return self._next if selector == SEL_NEXT_PAGE else None

    def wait_for_load_state(self, state: str, timeout: int = 0) -> None:
        pass


def _adapter() -> HandshakeAdapter:
    return HandshakeAdapter(ScraperSettings())


def test_parses_cards_with_job_ids() -> None:
    page = _Page(
        [
            _Card("/jobs/12345678", "SWE Intern", "Acme Corp", "Dallas, TX"),
            _Card("/jobs/87654321", "Data Analyst", "Initech", "Remote"),
        ]
    )
    jobs = _adapter().scrape_page(page)
    assert [j.posting_id for j in jobs] == ["12345678", "87654321"]
    assert jobs[0].title == "SWE Intern"
    assert jobs[0].employer == "Acme Corp"
    assert jobs[0].location == "Dallas, TX"
    assert jobs[0].portal_url == "https://app.joinhandshake.com/jobs/12345678"
    assert jobs[0].source_adapter == "handshake"


def test_card_without_job_id_is_skipped() -> None:
    page = _Page([_Card("/postings", "No id here", "X", "Y")])
    assert _adapter().scrape_page(page) == []


def test_next_page_clicks_enabled_button() -> None:
    btn = _El(enabled=True)
    page = _Page([], next_btn=btn)
    assert _adapter().next_page(page) is True
    assert btn.clicked is True


def test_next_page_stops_on_disabled_button() -> None:
    page = _Page([], next_btn=_El(enabled=False))
    assert _adapter().next_page(page) is False


def test_next_page_stops_when_no_button() -> None:
    page = _Page([], next_btn=None)
    assert _adapter().next_page(page) is False
