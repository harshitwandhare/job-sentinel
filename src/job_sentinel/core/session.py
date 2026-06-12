"""
core/session.py
────────────────
Shared session workflows used by both the CLI (``job-sentinel login`` /
``job-sentinel session``) and the local API (``/api/ops/login`` /
``/api/ops/session``). One implementation, two surfaces — they can't drift.

Two entry points:

``interactive_login``
    Opens a *visible* browser at the portal. As soon as a login form appears
    (Cloudflare-gated portals show it only after the user clears the
    challenge), the user's credentials from .env are prefilled so they just
    click "Sign In". When the authenticated app shell renders, the Playwright
    storage state (cookies) is saved for headless reuse.

``check_session``
    Headless, fast probe: loads the saved storage state and asks the adapter
    whether the portal still recognises it (e.g. via a current-user endpoint).
    No page navigation — a single HTTP request through the browser context.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from job_sentinel.adapters.base import SessionStatus
from job_sentinel.adapters.registry import get_adapter
from job_sentinel.core.browser import browser_context

if TYPE_CHECKING:
    from collections.abc import Callable

    from job_sentinel.config.settings import Settings


class LoginTimeoutError(RuntimeError):
    """The user didn't finish signing in before the timeout."""


def interactive_login(
    settings: Settings,
    timeout_seconds: int = 300,
    on_event: Callable[[str], None] | None = None,
) -> None:
    """
    Open a visible browser, prefill credentials when a login form appears,
    wait for the authenticated shell, then save the session state.

    Parameters
    ----------
    settings:
        Full app settings (portal credentials, session path, adapter id).
    timeout_seconds:
        How long to wait for the user to finish signing in.
    on_event:
        Optional progress callback (used by the API to surface status text).

    Raises
    ------
    LoginTimeoutError
        If no signed-in page was detected within the timeout.
    """
    notify = on_event or (lambda _msg: None)
    scraper = settings.scraper.model_copy(update={"headless": False})
    adapter = get_adapter(settings.site_adapter, scraper)

    ready = adapter.LOGGED_IN_SELECTOR
    sel_email = adapter.LOGIN_EMAIL_SELECTOR
    sel_password = adapter.LOGIN_PASSWORD_SELECTOR

    with browser_context(scraper) as ctx:
        page = ctx.new_page()
        page.goto(settings.portal.jobs_url, wait_until="domcontentloaded")
        notify("Browser open — finish signing in (credentials will be prefilled).")

        prefilled = False
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                if ready and page.query_selector(ready):
                    break
                if not prefilled and sel_email and sel_password:
                    email = page.query_selector(sel_email)
                    pwd = page.query_selector(sel_password)
                    if email and pwd and email.is_visible():
                        email.fill(settings.portal.username)
                        pwd.fill(settings.portal.password)
                        prefilled = True
                        notify("Credentials prefilled — click Sign In.")
                        logger.info("Login form prefilled from .env")
            except Exception as exc:
                # The page navigates mid-login (Cloudflare → form → portal);
                # selectors raise transiently. Retry on the next tick.
                logger.trace("Login poll tick failed (retrying): {}", exc)
            time.sleep(1.0)
        else:
            msg = "Didn't detect a signed-in page in time."
            raise LoginTimeoutError(msg)

        # Let the SPA finish bootstrapping so all auth cookies are set.
        page.wait_for_timeout(3_000)
        settings.session_path.parent.mkdir(parents=True, exist_ok=True)
        ctx.storage_state(path=str(settings.session_path))
        logger.info("Session saved | path={}", settings.session_path)


def check_session(settings: Settings) -> SessionStatus:
    """
    Probe whether the saved session is still valid, without opening any page.

    Returns a :class:`SessionStatus`; ``valid=False, checked=False`` means the
    adapter has no cheap probe (treat as unknown rather than expired).
    """
    if not settings.session_path.is_file():
        return SessionStatus(valid=False, detail="No saved session — log in first.")

    adapter = get_adapter(settings.site_adapter, settings.scraper)
    with browser_context(settings.scraper, storage_state=settings.session_path) as ctx:
        status = adapter.check_session(ctx)
    logger.info(
        "Session check | valid={} user={!r} detail={!r}",
        status.valid,
        status.user,
        status.detail,
    )
    return status
