"""
core/browser.py
────────────────
Playwright browser lifecycle manager.

Centralises all browser-launch configuration in one place so every
adapter gets the same hardened, WSL2-compatible Chromium instance.

Design
──────
• Context manager pattern — always cleans up even on exceptions
• WSL2 flags baked in (--no-sandbox, --disable-dev-shm-usage)
• Anti-detection headers / viewport to reduce bot-detection triggers
• Single BrowserContext per scrape cycle; adapters create Pages from it
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Playwright,
    sync_playwright,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from job_sentinel.config.settings import ScraperSettings

# Chrome args that make Playwright work reliably in WSL2 / Docker
_WSL2_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",  # WSL2 /dev/shm is tiny (64 MB)
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
    "--window-size=1280,900",
]

# Realistic user-agent string (keeps it close to a real Chrome release)
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


@contextmanager
def browser_context(
    settings: ScraperSettings,
    storage_state: str | Path | None = None,
) -> Generator[BrowserContext, None, None]:
    """
    Context manager that yields a ready-to-use :class:`BrowserContext`.

    Usage::

        with browser_context(settings, storage_state="data/session.json") as ctx:
            adapter.scrape(ctx)

    The browser and context are fully torn down on exit, even if an
    exception is raised inside the ``with`` block.

    Parameters
    ----------
    settings : ScraperSettings
        Provides headless flag, slow-mo, and timeout values.
    storage_state :
        Optional path to a Playwright storage-state file (cookies + local
        storage) saved by ``job-sentinel login``. When it exists, the context
        starts already authenticated — which is how we get past Duo MFA without
        re-logging-in every cycle. Ignored if the path is missing.
    """
    playwright: Playwright | None = None
    browser: Browser | None = None

    state_path = Path(storage_state) if storage_state else None
    use_state = str(state_path) if state_path and state_path.is_file() else None

    try:
        logger.debug(
            "Launching Chromium | headless={} session={}",
            settings.headless,
            "reused" if use_state else "fresh",
        )
        playwright = sync_playwright().start()

        browser = playwright.chromium.launch(
            headless=settings.headless,
            slow_mo=settings.browser_slowmo_ms,
            args=_WSL2_ARGS,
        )

        context: BrowserContext = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/Chicago",  # UTD is Central Time
            java_script_enabled=True,
            storage_state=use_state,
            # Tell the site we accept cookies — avoids cookie-wall popups
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )

        # Stealth: remove webdriver flag
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        logger.debug("Browser context ready")
        yield context

    finally:
        if browser:
            try:
                browser.close()
                logger.debug("Browser closed")
            except Exception as exc:
                logger.warning("Error closing browser: {}", exc)
        if playwright:
            try:
                playwright.stop()
            except Exception as exc:
                logger.warning("Error stopping Playwright: {}", exc)
