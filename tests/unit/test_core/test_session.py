"""
Tests for the shared session workflows (interactive login + validity check).

The browser is faked at the ``browser_context`` boundary so no Chromium runs.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest

import job_sentinel.core.session as session_mod
from job_sentinel.adapters.base import SessionStatus
from job_sentinel.core.session import LoginTimeoutError, check_session, interactive_login


class _FakeElement:
    def __init__(self) -> None:
        self.filled: list[str] = []

    def is_visible(self) -> bool:
        return True

    def fill(self, value: str) -> None:
        self.filled.append(value)


class _FakePage:
    """Login form on tick 1; authenticated shell from tick 3 onward."""

    def __init__(self) -> None:
        self.tick = 0
        self.email = _FakeElement()
        self.password = _FakeElement()

    def goto(self, url: str, wait_until: str = "") -> None:
        pass

    def query_selector(self, selector: str) -> Any:
        self.tick += 1
        if "logout" in selector or "side-nav" in selector:
            return _FakeElement() if self.tick >= 3 else None
        if "email" in selector or "username" in selector:
            return self.email
        if "password" in selector:
            return self.password
        return None

    def wait_for_timeout(self, ms: int) -> None:
        pass


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self._page = page
        self.saved_to: str | None = None

    def new_page(self) -> _FakePage:
        return self._page

    def storage_state(self, path: str) -> None:
        self.saved_to = path


class _FakeAdapter:
    LOGGED_IN_SELECTOR = "#side-nav a.side-nav-link, a.logout"
    LOGIN_EMAIL_SELECTOR = "input[type='email']"
    LOGIN_PASSWORD_SELECTOR = "input[type='password']"

    def __init__(self, status: SessionStatus | None = None) -> None:
        self._status = status or SessionStatus(valid=True, user="Test User")

    def check_session(self, context: Any) -> SessionStatus:
        return self._status


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """Real Settings with portal/session bits pointed at temp locations."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("PORTAL_USERNAME", "user@example.com")
    monkeypatch.setenv("PORTAL_PASSWORD", "hunter2")
    monkeypatch.setenv("PORTAL_JOBS_URL", "https://example.12twenty.com/jobPostings")
    from job_sentinel.config.settings import Settings

    s = Settings()
    s.session_path = tmp_path / "session.json"
    return s


def _patch_browser(monkeypatch, ctx: _FakeContext) -> None:
    @contextmanager
    def fake_browser_context(scraper_settings, storage_state=None):
        yield ctx

    monkeypatch.setattr(session_mod, "browser_context", fake_browser_context)


def test_interactive_login_prefills_and_saves(settings, monkeypatch) -> None:
    page = _FakePage()
    ctx = _FakeContext(page)
    _patch_browser(monkeypatch, ctx)
    monkeypatch.setattr(session_mod, "get_adapter", lambda *a, **k: _FakeAdapter())
    monkeypatch.setattr(session_mod.time, "sleep", lambda s: None)

    events: list[str] = []
    interactive_login(settings, timeout_seconds=30, on_event=events.append)

    assert page.email.filled == ["user@example.com"]
    assert page.password.filled == ["hunter2"]
    assert ctx.saved_to == str(settings.session_path)
    assert any("prefilled" in e.lower() for e in events)


def test_interactive_login_times_out(settings, monkeypatch) -> None:
    page = _FakePage()
    page.query_selector = lambda selector: None  # nothing ever renders
    _patch_browser(monkeypatch, _FakeContext(page))
    monkeypatch.setattr(session_mod, "get_adapter", lambda *a, **k: _FakeAdapter())
    monkeypatch.setattr(session_mod.time, "sleep", lambda s: None)

    clock = iter(range(0, 10_000))
    monkeypatch.setattr(session_mod.time, "monotonic", lambda: float(next(clock)))

    with pytest.raises(LoginTimeoutError):
        interactive_login(settings, timeout_seconds=5)


def test_check_session_without_file(settings) -> None:
    status = check_session(settings)
    assert status.valid is False
    assert "log in" in status.detail.lower()


def test_check_session_valid(settings, monkeypatch) -> None:
    settings.session_path.write_text("{}", encoding="utf-8")
    _patch_browser(monkeypatch, _FakeContext(_FakePage()))
    monkeypatch.setattr(
        session_mod,
        "get_adapter",
        lambda *a, **k: _FakeAdapter(SessionStatus(valid=True, user="Harshit")),
    )

    status = check_session(settings)
    assert status.valid is True
    assert status.user == "Harshit"


def test_check_session_expired(settings, monkeypatch) -> None:
    settings.session_path.write_text("{}", encoding="utf-8")
    _patch_browser(monkeypatch, _FakeContext(_FakePage()))
    monkeypatch.setattr(
        session_mod,
        "get_adapter",
        lambda *a, **k: _FakeAdapter(SessionStatus(valid=False, detail="HTTP 401")),
    )

    status = check_session(settings)
    assert status.valid is False
    assert status.detail == "HTTP 401"
