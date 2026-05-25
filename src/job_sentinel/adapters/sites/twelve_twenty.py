"""
adapters/sites/twelve_twenty.py
────────────────────────────────
Site adapter for **12twenty** portals (UTD and other universities).

12twenty is a SPA (Single-Page Application) that requires:
  1. CAS (Central Authentication Service) login — redirected to
     ``login.utdallas.edu`` before any job data is accessible.
  2. Navigation to the "Student Employment" tab.
  3. Waiting for React-rendered job cards to hydrate.

Selector strategy
─────────────────
All CSS selectors are defined as module-level constants.
If the portal's DOM changes, update only this section — no logic code
needs to change.

The adapter is registered automatically when this module is imported
(via ``register_adapter`` at module bottom).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from loguru import logger
from playwright.sync_api import ElementHandle, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.adapters.registry import register_adapter
from job_sentinel.core.models import JobPosting

if TYPE_CHECKING:
    from job_sentinel.config.settings import ScraperSettings

# ─────────────────────────────────────────────────────────────────────────────
# Portal constants
# ─────────────────────────────────────────────────────────────────────────────

PORTAL_BASE_URL = "https://utdallas.12twenty.com"
CAS_LOGIN_DOMAIN = "login.utdallas.edu"

# ── CSS Selectors (update here if 12twenty changes its DOM) ──────────────────
SEL_USERNAME = "input#username"
SEL_PASSWORD = "input#password"  # noqa: S105 — CSS selector, not a credential
SEL_LOGIN_BTN = "input[type='submit'], button[type='submit']"
SEL_JOB_CARD = ".posting-card, [data-posting-id], .job-posting-item, .posting-list-item"
SEL_JOB_TITLE = ".posting-title, .job-title, h3.title, h2.title, [class*='title']"
SEL_EMPLOYER = ".employer-name, .company-name, .organization, [class*='employer']"
SEL_LOCATION = ".location, .job-location, [class*='location']"
SEL_JOB_TYPE = ".job-type, .employment-type, .posting-type, [class*='type']"
SEL_POSTED_DATE = ".posted-date, .date-posted, time, [class*='posted']"
SEL_DEADLINE = ".deadline, .application-deadline, .close-date, [class*='deadline']"
SEL_NEXT_PAGE = "[aria-label='Next page'], .pagination-next, button.next-page, [class*='next']"
SEL_DESCRIPTION = ".description, .job-description, [class*='description'] p"


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

    def __init__(self, scraper_settings: ScraperSettings) -> None:
        super().__init__(scraper_settings)
        self._jobs_url: str = ""  # set from portal settings at scrape time

    # ── Login ──────────────────────────────────────────────────────────────

    def login(self, page: Page) -> None:
        """
        Navigate to the portal and complete CAS SSO authentication.

        After this method returns, ``page`` is on the job-listings tab
        with the SPA fully hydrated.
        """
        from job_sentinel.config.settings import get_settings  # lazy import

        settings = get_settings()
        self._jobs_url = settings.portal.jobs_url
        username = settings.portal.username
        password = settings.portal.password

        logger.info("Navigating to portal | url={}", self._jobs_url)
        page.goto(self._jobs_url, wait_until="domcontentloaded")

        # CAS redirect check
        if CAS_LOGIN_DOMAIN in page.url:
            logger.info("CAS login page detected — submitting credentials")
            page.fill(SEL_USERNAME, username)
            page.fill(SEL_PASSWORD, password)
            page.click(SEL_LOGIN_BTN)
            # Wait for redirect back to 12twenty after successful auth
            page.wait_for_url(f"*{PORTAL_BASE_URL}*", timeout=60_000)
            logger.info("CAS authentication successful")
        else:
            logger.debug("No CAS redirect — session already active")

        # Let the SPA finish rendering
        page.wait_for_load_state("networkidle", timeout=self._settings.page_timeout_ms)

        # Ensure we're on the studentEmployment tab
        if "studentEmployment" not in page.url:
            logger.debug("Navigating to studentEmployment tab")
            page.goto(self._jobs_url, wait_until="networkidle")

    # ── Page scraping ──────────────────────────────────────────────────────

    def scrape_page(self, page: Page) -> list[JobPosting]:
        """Extract all job cards visible on the current page."""
        try:
            page.wait_for_selector(SEL_JOB_CARD, timeout=self._settings.page_timeout_ms)
        except PlaywrightTimeoutError:
            logger.warning("No job cards found — page may be empty or selector is stale")
            return []

        cards = page.query_selector_all(SEL_JOB_CARD)
        logger.debug("Found {} cards on page", len(cards))

        jobs = []
        for card in cards:
            job = self._parse_card(card, page)
            if job:
                jobs.append(job)

        return jobs

    # ── Pagination ─────────────────────────────────────────────────────────

    def next_page(self, page: Page) -> bool:
        """Click the next-page button if present and enabled."""
        btn = page.query_selector(SEL_NEXT_PAGE)
        if not btn or not btn.is_enabled():
            return False

        btn.click()
        page.wait_for_load_state("networkidle", timeout=self._settings.page_timeout_ms)
        return True

    # ── Card parsing ───────────────────────────────────────────────────────

    def _parse_card(self, card: ElementHandle, page: Page) -> JobPosting | None:
        """Parse a single job card element into a :class:`JobPosting`."""
        try:
            # ── Extract posting ID ──────────────────────────────────────
            posting_id = (
                self.safe_attr(card, "", "data-posting-id")
                or self.safe_attr(card, "", "data-id")
                or self.safe_attr(card, "", "id")
            )

            # Fallback: parse ID from anchor href
            if not posting_id:
                link = card.query_selector("a[href]")
                if link:
                    href = link.get_attribute("href") or ""
                    m = re.search(r"postings?/(\d+)", href)
                    if m:
                        posting_id = m.group(1)

            if not posting_id:
                logger.debug("Skipping card — could not extract posting_id")
                return None

            # ── Extract text fields ─────────────────────────────────────
            title = self.safe_text(card, SEL_JOB_TITLE) or "Untitled Position"
            employer = self.safe_text(card, SEL_EMPLOYER)
            location = self.safe_text(card, SEL_LOCATION)
            job_type = self.safe_text(card, SEL_JOB_TYPE)
            posted_date = self.safe_text(card, SEL_POSTED_DATE)
            deadline = self.safe_text(card, SEL_DEADLINE)

            # ── Description snippet ─────────────────────────────────────
            snippet_el = card.query_selector(SEL_DESCRIPTION)
            snippet = snippet_el.inner_text().strip() if snippet_el else ""

            # ── Build absolute portal URL ───────────────────────────────
            link_el = card.query_selector("a")
            href = (link_el.get_attribute("href") or "") if link_el else ""
            portal_url = self.absolute_url(href) if href else page.url

            return JobPosting(
                posting_id=posting_id,
                title=title,
                employer=employer,
                location=location,
                job_type=job_type,
                posted_date=posted_date,
                deadline=deadline,
                description_snippet=snippet,
                portal_url=portal_url,
                source_adapter=self.ADAPTER_ID,
                raw_data={"scraped_url": page.url},
            )

        except Exception as exc:
            logger.warning("Failed to parse job card: {}", exc)
            return None


# ── Self-register when this module is imported ────────────────────────────────
register_adapter(TwelveTwentyAdapter)
