"""
adapters/sites/twelve_twenty.py
────────────────────────────────
Site adapter for **12twenty** portals (UTD and other universities).

12twenty is an AngularJS single-page app. Reaching the job data takes:
  1. CAS (Central Authentication Service) login — redirected to
     ``login.utdallas.edu`` before any job data is accessible.
  2. Landing on the "Student Employment" tab (``tab=studentEmployment``).
  3. Waiting for the results table to render, then scrolling to pull in
     lazily-loaded rows (the list has no numbered pager).

Selector strategy
─────────────────
All CSS selectors live in the constants block below. The listing selectors
were verified against the live UTD Student Employment DOM (2026-06): each
posting is a ``tr.job-posting`` row inside the results table, with the title
in ``a.job-title`` and the secondary details in ``span.sub-info`` /
``span.sub-info-item`` elements. If 12twenty reskins its markup, this block is
the only thing that should need touching.

The adapter is registered automatically when this module is imported
(via ``register_adapter`` at module bottom).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from loguru import logger
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.adapters.registry import register_adapter
from job_sentinel.core.models import JobPosting

if TYPE_CHECKING:
    from playwright.sync_api import ElementHandle

    from job_sentinel.config.settings import ScraperSettings

# ─────────────────────────────────────────────────────────────────────────────
# Portal constants
# ─────────────────────────────────────────────────────────────────────────────

PORTAL_BASE_URL = "https://utdallas.12twenty.com"

# ── Login form (12twenty's own email/password form — no SSO) ─────────────────
# The live login page sits behind a Cloudflare Turnstile challenge, so the
# reliable path is to reuse a session captured by `job-sentinel login`. These
# selectors are a best-effort fallback for when the form is reachable directly.
SEL_EMAIL = "input[type='email'], input[name='email'], input#email"
SEL_PASSWORD = "input[type='password'], input#password"  # noqa: S105 — selector, not a secret
SEL_LOGIN_BTN = "button[type='submit'], input[type='submit']"

# ── Listing (verified against the live 12twenty Student Employment DOM) ──────
SEL_JOB_CARD = "tr.job-posting"
SEL_TITLE_LINK = "a.job-title"
SEL_JOB_TITLE = "a.job-title .primary-item-text"
# The employer is the one .sub-info block that holds bound text directly rather
# than a list of .sub-info-item children.
SEL_EMPLOYER = "span.sub-info:not(:has(span.sub-info-item))"
SEL_SUB_ITEM = "span.sub-info-item"
SEL_DEADLINE = "tt-date-time-display"

# Posting id lives in the title href: …#/jobPostings/<digits>
_POSTING_ID_RE = re.compile(r"/jobPostings/(\d+)")
# "5 days ago", "1 week ago", "today", "yesterday" — relative posted date.
_POSTED_RE = re.compile(r"\b(ago|today|yesterday)\b", re.IGNORECASE)


class TwelveTwentyAdapter(SiteAdapter):
    """
    Scraper for 12twenty job portals (UTD Student Employment and others).

    Configured via:
      - ``PORTAL_JOBS_URL``  — the full URL to the listings tab
      - ``PORTAL_USERNAME``  — UTD Net ID / email
      - ``PORTAL_PASSWORD``  — UTD password
    """

    ADAPTER_ID = "12twenty"
    ADAPTER_NAME = "12twenty Portal"
    BASE_URL = PORTAL_BASE_URL
    LOGGED_IN_SELECTOR = SEL_JOB_CARD

    def __init__(self, scraper_settings: ScraperSettings) -> None:
        super().__init__(scraper_settings)
        self._jobs_url: str = ""  # set from portal settings at scrape time

    # ── Login ──────────────────────────────────────────────────────────────

    def login(self, page: Page) -> None:
        """
        Reach the authenticated job-listings view.

        Preferred path: a session saved by ``job-sentinel login`` is already
        loaded into the browser context, so navigating straight to the jobs URL
        renders the listing. If we land on the login form instead (session
        expired), we attempt a direct email/password submit — but note the live
        login page is Cloudflare-gated, so that fallback often won't get
        through; the user should re-run ``job-sentinel login`` in that case.
        """
        from job_sentinel.config.settings import get_settings  # lazy import

        settings = get_settings()
        self._jobs_url = settings.portal.jobs_url
        timeout = self._settings.page_timeout_ms

        logger.info("Navigating to portal | url={}", self._jobs_url)
        page.goto(self._jobs_url, wait_until="domcontentloaded")

        # Already authenticated via a reused session? The listing renders.
        try:
            page.wait_for_selector(self.LOGGED_IN_SELECTOR, timeout=8_000)
            logger.debug("Session active — listing rendered")
            return
        except PlaywrightTimeoutError:
            logger.debug("Listing not visible yet — checking for a login form")

        email = page.query_selector(SEL_EMAIL)
        pwd = page.query_selector(SEL_PASSWORD)
        if email and pwd:
            logger.info("Login form detected — submitting credentials")
            email.fill(settings.portal.username)
            pwd.fill(settings.portal.password)
            btn = page.query_selector(SEL_LOGIN_BTN)
            (btn or pwd).click() if btn else pwd.press("Enter")
            page.wait_for_selector(self.LOGGED_IN_SELECTOR, timeout=timeout)
        else:
            msg = (
                "Not authenticated and no login form is reachable (the 12twenty "
                "login is behind a Cloudflare challenge). Run `job-sentinel login` "
                "to sign in once and save the session."
            )
            raise RuntimeError(msg)

    # ── Page scraping ──────────────────────────────────────────────────────

    def scrape_page(self, page: Page) -> list[JobPosting]:
        """Extract every job row, scrolling to pull in lazily-loaded ones."""
        try:
            page.wait_for_selector(SEL_JOB_CARD, timeout=self._settings.page_timeout_ms)
        except PlaywrightTimeoutError:
            logger.warning("No job rows found — list may be empty or the selector is stale")
            return []

        self._load_all_rows(page)

        cards = page.query_selector_all(SEL_JOB_CARD)
        logger.debug("Found {} rows after scrolling", len(cards))

        jobs = []
        for card in cards:
            job = self._parse_card(card, page)
            if job:
                jobs.append(job)
        return jobs

    def next_page(self, page: Page) -> bool:
        """
        12twenty has no numbered pager — everything for a search lives in one
        lazily-extended table that :meth:`scrape_page` already exhausts via
        scrolling. So there is never a "next page" to advance to.
        """
        return False

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _load_all_rows(self, page: Page) -> None:
        """Scroll to the bottom until the row count stops growing (lazy load)."""
        previous = -1
        # Bound the loop so a misbehaving page can't spin forever.
        for _ in range(self._settings.max_pages):
            count = len(page.query_selector_all(SEL_JOB_CARD))
            if count == previous:
                break
            previous = count
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            try:
                page.wait_for_function(
                    "(n) => document.querySelectorAll('tr.job-posting').length > n",
                    arg=count,
                    timeout=2_000,
                )
            except PlaywrightTimeoutError:
                break  # nothing new loaded — we've reached the end

    def _parse_card(self, card: ElementHandle, page: Page) -> JobPosting | None:
        """Parse a single ``tr.job-posting`` row into a :class:`JobPosting`."""
        try:
            link = card.query_selector(SEL_TITLE_LINK)
            href = (link.get_attribute("href") or "") if link else ""
            match = _POSTING_ID_RE.search(href)
            if not match:
                logger.debug("Skipping row — no posting id in href {!r}", href)
                return None
            posting_id = match.group(1)

            title = self.safe_text(card, SEL_JOB_TITLE)
            if not title and link:
                title = link.inner_text().strip()
            title = title or "Untitled Position"

            employer = self.safe_text(card, SEL_EMPLOYER)

            # location / type / posted-date all share the .sub-info-item class,
            # so classify them by content rather than by a brittle index.
            items = [el.inner_text().strip() for el in card.query_selector_all(SEL_SUB_ITEM)]
            items = [i for i in items if i]
            posted_date = next((i for i in items if _POSTED_RE.search(i)), "")
            descriptive = [
                i for i in items if not _POSTED_RE.search(i) and not i.lower().startswith("apply")
            ]
            location = descriptive[0] if descriptive else ""
            job_type = descriptive[1] if len(descriptive) > 1 else ""

            deadline = self.safe_text(card, SEL_DEADLINE)

            return JobPosting(
                posting_id=posting_id,
                title=title,
                employer=employer,
                location=location,
                job_type=job_type,
                posted_date=posted_date,
                deadline=deadline,
                portal_url=self.absolute_url(href) if href else page.url,
                source_adapter=self.ADAPTER_ID,
                raw_data={"scraped_url": page.url},
            )

        except Exception as exc:
            logger.warning("Failed to parse job row: {}", exc)
            return None


# ── Self-register when this module is imported ────────────────────────────────
register_adapter(TwelveTwentyAdapter)
