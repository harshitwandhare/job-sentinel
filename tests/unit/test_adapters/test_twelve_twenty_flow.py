"""
Flow tests for the 12twenty adapter: login branching, API capture, and
scrape_page source selection — against a fake Playwright page (no browser).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_sentinel.adapters.sites.twelve_twenty import (
    SEL_APP_SHELL,
    TwelveTwentyAdapter,
)
from job_sentinel.config.settings import ScraperSettings


class _El:
    def __init__(self) -> None:
        self.filled: list[str] = []
        self.clicked = False

    def fill(self, value: str) -> None:
        self.filled.append(value)

    def click(self) -> None:
        self.clicked = True

    def press(self, key: str) -> None:
        self.clicked = True

    def is_visible(self) -> bool:
        return True


class _FakeResponse:
    """Mimics a Playwright Response for the post-query listener."""

    def __init__(self, url: str, status: int = 200, body: Any = None) -> None:
        self.url = url
        self.status = status
        self._body = body

    def json(self) -> Any:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _FakePage:
    """Just enough Page surface for login() + scrape_page()."""

    def __init__(
        self,
        *,
        shell: bool = False,
        login_form: bool = False,
        body_text: str = "",
        rows: int = 0,
    ) -> None:
        self.shell = shell
        self.login_form = login_form
        self.body_text = body_text
        self.rows = rows
        self.listeners: list[Any] = []
        self.email = _El()
        self.password = _El()
        self.submit = _El()
        self.context = SimpleNamespace(request=SimpleNamespace(get=self._req_get))
        self.detail_responses: dict[str, Any] = {}

    # navigation / waiting -------------------------------------------------
    def on(self, event: str, handler: Any) -> None:
        self.listeners.append(handler)

    def goto(self, url: str, wait_until: str = "") -> None:
        self.url = url

    def wait_for_selector(self, selector: str, timeout: int = 0) -> None:
        if "password" in selector and (self.shell or self.login_form):
            return  # combined shell-or-login wait
        if selector == SEL_APP_SHELL and self.shell:
            return
        if "tr.job-posting" in selector and self.rows:
            return
        raise PlaywrightTimeoutError("not found")

    def wait_for_function(self, fn: str, arg: Any = None, timeout: int = 0) -> None:
        raise PlaywrightTimeoutError("no more rows")

    def wait_for_timeout(self, ms: int) -> None:
        pass

    def evaluate(self, script: str) -> None:
        pass

    # querying ---------------------------------------------------------------
    def query_selector(self, selector: str):
        if selector == SEL_APP_SHELL:
            return _El() if self.shell else None
        if self.login_form:
            if "email" in selector or "username" in selector:
                return self.email
            if "password" in selector:
                return self.password
            if "submit" in selector:
                return self.submit
        return None

    def query_selector_all(self, selector: str) -> list:
        return [_El()] * self.rows if "tr.job-posting" in selector else []

    def inner_text(self, selector: str, timeout: int = 0) -> str:
        return self.body_text

    # detail fetches ----------------------------------------------------------
    def _req_get(self, url: str, timeout: int = 0) -> Any:
        posting_id = url.rstrip("/").rsplit("/", 1)[-1]
        body = self.detail_responses.get(posting_id, {})
        return SimpleNamespace(ok=True, status=200, json=lambda: body)


def _adapter(monkeypatch: pytest.MonkeyPatch) -> TwelveTwentyAdapter:
    """Adapter whose settings lookup is faked (no real .env needed)."""
    adapter = TwelveTwentyAdapter(ScraperSettings(page_timeout_ms=5_000))
    fake_settings = SimpleNamespace(
        portal=SimpleNamespace(
            jobs_url="https://u.12twenty.com/jobPostings#/jobPostings/index"
            "?viewId=6&tab=studentEmployment",
            username="me@utd.edu",
            password="secret",
        )
    )
    import job_sentinel.config.settings as settings_mod

    monkeypatch.setattr(settings_mod, "get_settings", lambda: fake_settings)
    return adapter


_API_ITEM = {
    "Id": 111,
    "TitleDisplay": "Lab Assistant",
    "CompanyName": "UT Dallas - Physics",
    "LocationDisplay": "Richardson - TX",
    "JobPostingJobTypeNames": "Part-Time Job",
    "PostedDate": "2026-06-10T19:30:14",
    "ApplicationDeadlineDate": "2026-06-17T22:00:00",
}


# ── login() ──────────────────────────────────────────────────────────────────


def test_login_with_valid_session_strips_view_id(monkeypatch) -> None:
    adapter = _adapter(monkeypatch)
    page = _FakePage(shell=True)
    adapter.login(page)
    assert "viewId" not in adapter._jobs_url
    assert "tab=studentEmployment" in adapter._jobs_url


def test_login_fills_credentials_when_form_shown(monkeypatch) -> None:
    adapter = _adapter(monkeypatch)
    page = _FakePage(login_form=True)

    # After the submit click, the shell "renders".
    original_click = page.submit.click

    def click_and_authenticate() -> None:
        original_click()
        page.shell = True

    page.submit.click = click_and_authenticate

    adapter.login(page)
    assert page.email.filled == ["me@utd.edu"]
    assert page.password.filled == ["secret"]
    assert page.submit.clicked is True


def test_login_raises_when_nothing_renders(monkeypatch) -> None:
    adapter = _adapter(monkeypatch)
    with pytest.raises(RuntimeError, match="job-sentinel login"):
        adapter.login(_FakePage())


def test_login_dismisses_not_authorized_modal(monkeypatch) -> None:
    adapter = _adapter(monkeypatch)
    page = _FakePage(shell=True, body_text="Oops! Sorry! You are not authorized.")
    adapter.login(page)  # should not raise; modal handling is best-effort


# ── API capture + scrape_page() ──────────────────────────────────────────────


def test_capture_collects_and_dedupes_items(monkeypatch) -> None:
    adapter = _adapter(monkeypatch)
    resp = _FakeResponse(
        "https://u.12twenty.com/Api/V2/job-postings/post-query",
        body={"Items": [_API_ITEM, _API_ITEM]},
    )
    adapter._capture_post_query(resp)
    adapter._capture_post_query(resp)  # second page returning same item
    assert list(adapter._api_items) == ["111"]


def test_capture_ignores_other_endpoints_and_errors(monkeypatch) -> None:
    adapter = _adapter(monkeypatch)
    adapter._capture_post_query(_FakeResponse("https://u.12twenty.com/api/other", body={}))
    adapter._capture_post_query(
        _FakeResponse("https://u.12twenty.com/Api/V2/job-postings/post-query", status=500)
    )
    adapter._capture_post_query(
        _FakeResponse(
            "https://u.12twenty.com/Api/V2/job-postings/post-query",
            body=ValueError("not json"),
        )
    )
    assert adapter._api_items == {}


def test_scrape_page_prefers_api_items_and_enriches(monkeypatch) -> None:
    adapter = _adapter(monkeypatch)
    adapter._api_items["111"] = _API_ITEM
    page = _FakePage(rows=1)
    page.detail_responses["111"] = {
        "Description": "<p>Assist in the <b>physics</b> lab.</p>",
        "BaseSalary": 12.0,
        "CurrencyName": "USD",
        "PayFormatName": "per hour",
    }

    jobs = adapter.scrape_page(page)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Lab Assistant"
    assert job.posted_date == "2026-06-10"
    assert "physics lab" in job.description_snippet
    assert job.raw_data["detail"]["salary"] == "12.0 USD per hour"


def test_scrape_page_empty_when_no_rows_and_no_api(monkeypatch) -> None:
    adapter = _adapter(monkeypatch)
    assert adapter.scrape_page(_FakePage(rows=0)) == []


def test_next_page_is_always_false(monkeypatch) -> None:
    assert _adapter(monkeypatch).next_page(_FakePage()) is False
