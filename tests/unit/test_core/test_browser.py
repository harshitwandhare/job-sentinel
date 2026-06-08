"""Tests for the Playwright browser context manager (Playwright itself mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

import job_sentinel.core.browser as browser_mod
from job_sentinel.config.settings import ScraperSettings


def test_browser_context_yields_and_tears_down(monkeypatch) -> None:
    fake_context = MagicMock(name="context")
    fake_browser = MagicMock(name="browser")
    fake_browser.new_context.return_value = fake_context
    fake_pw = MagicMock(name="playwright")
    fake_pw.chromium.launch.return_value = fake_browser

    start = MagicMock(return_value=fake_pw)
    monkeypatch.setattr(browser_mod, "sync_playwright", lambda: MagicMock(start=start))

    with browser_mod.browser_context(ScraperSettings(headless=True)) as ctx:
        assert ctx is fake_context

    # Launch flags include the WSL2-safe args.
    _, kwargs = fake_browser.new_context.call_args
    assert kwargs["locale"] == "en-US"
    fake_context.add_init_script.assert_called_once()
    # Teardown happened.
    fake_browser.close.assert_called_once()
    fake_pw.stop.assert_called_once()


def test_browser_context_tears_down_on_exception(monkeypatch) -> None:
    fake_browser = MagicMock(name="browser")
    fake_browser.new_context.return_value = MagicMock()
    fake_pw = MagicMock(name="playwright")
    fake_pw.chromium.launch.return_value = fake_browser
    monkeypatch.setattr(
        browser_mod, "sync_playwright", lambda: MagicMock(start=MagicMock(return_value=fake_pw))
    )

    try:
        with browser_mod.browser_context(ScraperSettings()):
            raise ValueError("boom")
    except ValueError:
        pass

    fake_browser.close.assert_called_once()
    fake_pw.stop.assert_called_once()
