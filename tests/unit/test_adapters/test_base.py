"""Tests for the SiteAdapter base class: helpers + the scrape() orchestrator."""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.config.settings import ScraperSettings
from job_sentinel.core.models import JobPosting


class _FakePage:
    def __init__(self) -> None:
        self.closed = False

    def set_default_timeout(self, _ms: int) -> None:
        pass

    def close(self) -> None:
        self.closed = True


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self._page = page

    def new_page(self) -> _FakePage:
        return self._page


class _FakeElement:
    def __init__(self, text: str = "", attrs: dict | None = None) -> None:
        self._text = text
        self._attrs = attrs or {}

    def inner_text(self) -> str:
        return self._text

    def get_attribute(self, name: str) -> str | None:
        return self._attrs.get(name)

    def query_selector(self, _selector: str) -> _FakeElement | None:
        return self


class _PagingAdapter(SiteAdapter):
    """Yields one job on the first page, then paginates once to an empty page."""

    ADAPTER_ID = "_paging"
    BASE_URL = "https://example.com"

    def __init__(self, settings: ScraperSettings) -> None:
        super().__init__(settings)
        self.logged_in = False
        self._page_index = 0

    def login(self, page) -> None:
        self.logged_in = True

    def scrape_page(self, page) -> list[JobPosting]:
        if self._page_index == 0:
            return [JobPosting(posting_id="p1", title="First", source_adapter=self.ADAPTER_ID)]
        return []

    def next_page(self, page) -> bool:
        if self._page_index == 0:
            self._page_index += 1
            return True
        return False


def _settings() -> ScraperSettings:
    return ScraperSettings(page_timeout_ms=5000, max_pages=10)


def test_scrape_logs_in_and_paginates() -> None:
    page = _FakePage()
    adapter = _PagingAdapter(_settings())
    jobs = adapter.scrape(_FakeContext(page))

    assert adapter.logged_in is True
    assert [j.posting_id for j in jobs] == ["p1"]
    assert page.closed is True  # page is always closed in finally


class _TimeoutAdapter(SiteAdapter):
    ADAPTER_ID = "_timeout"
    BASE_URL = "https://example.com"

    def login(self, page) -> None:
        pass

    def scrape_page(self, page) -> list[JobPosting]:
        raise PlaywrightTimeoutError("boom")


def test_scrape_survives_page_timeout() -> None:
    page = _FakePage()
    adapter = _TimeoutAdapter(_settings())
    jobs = adapter.scrape(_FakeContext(page))
    assert jobs == []
    assert page.closed is True


class _MinimalAdapter(SiteAdapter):
    ADAPTER_ID = "_minimal"
    BASE_URL = "https://example.com/base/"

    def login(self, page) -> None:
        pass

    def scrape_page(self, page) -> list[JobPosting]:
        return []


class TestHelpers:
    def test_absolute_url_relative(self) -> None:
        a = _MinimalAdapter(_settings())
        assert a.absolute_url("jobs/1") == "https://example.com/base/jobs/1"

    def test_absolute_url_absolute_passthrough(self) -> None:
        a = _MinimalAdapter(_settings())
        assert a.absolute_url("https://other.com/x") == "https://other.com/x"

    def test_absolute_url_empty_returns_base(self) -> None:
        a = _MinimalAdapter(_settings())
        assert a.absolute_url("") == "https://example.com/base/"

    def test_safe_text_reads_inner_text(self) -> None:
        el = _FakeElement(text="  hello  ")
        assert SiteAdapter.safe_text(el, ".sel") == "hello"

    def test_safe_attr_reads_attribute(self) -> None:
        el = _FakeElement(attrs={"href": "/jobs/9"})
        assert SiteAdapter.safe_attr(el, ".sel", "href") == "/jobs/9"

    def test_safe_text_never_raises(self) -> None:
        class _Bad:
            def query_selector(self, _s):
                raise RuntimeError("nope")

        assert SiteAdapter.safe_text(_Bad(), ".sel") == ""
