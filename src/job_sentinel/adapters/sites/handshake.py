"""
adapters/sites/handshake.py
────────────────────────────
Site adapter for **Handshake** (joinhandshake.com).

Handshake is widely used by US universities for recruiting.
This adapter is a starting point — the selectors and login flow
need to be tuned to the authenticated Handshake SPA.

Status: BETA  — community contributions welcome.
See: https://github.com/harshitwandhare/job-sentinel/issues

To activate:
    SITE_ADAPTER=handshake
    PORTAL_JOBS_URL=https://app.joinhandshake.com/stu/postings
"""

from __future__ import annotations

from loguru import logger
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.adapters.registry import register_adapter
from job_sentinel.core.models import JobPosting

# ── Selectors (tune these for Handshake's current DOM) ───────────────────────
SEL_EMAIL_INPUT = "input[type='email'], input[name='email']"
SEL_PASSWORD = "input[type='password']"  # noqa: S105 — CSS selector, not a credential
SEL_SUBMIT_BTN = "button[type='submit']"
SEL_JOB_CARD = "[data-hook='jobs-card'], .posting-card, [class*='JobCard']"
SEL_TITLE = "[data-hook='jobs-card-title'], h3, [class*='title']"
SEL_EMPLOYER = "[data-hook='jobs-card-employer'], [class*='employer']"
SEL_LOCATION = "[data-hook='jobs-card-location'], [class*='location']"
SEL_NEXT_PAGE = "[aria-label='Next Page'], button[rel='next']"


class HandshakeAdapter(SiteAdapter):
    """
    Scraper for Handshake job portals.

    Supports SSO-less email/password login.
    For SSO institutions, extend ``login()`` to handle the IdP redirect.
    """

    ADAPTER_ID = "handshake"
    ADAPTER_NAME = "Handshake"
    BASE_URL = "https://app.joinhandshake.com"

    def login(self, page: Page) -> None:
        from job_sentinel.config.settings import get_settings

        s = get_settings()
        jobs_url = s.portal.jobs_url

        logger.info("Navigating to Handshake | url={}", jobs_url)
        page.goto(jobs_url, wait_until="domcontentloaded")

        # Handle login wall if redirected
        if "sign_in" in page.url or "login" in page.url.lower():
            logger.info("Login page detected — submitting credentials")
            page.fill(SEL_EMAIL_INPUT, s.portal.username)
            page.fill(SEL_PASSWORD, s.portal.password)
            page.click(SEL_SUBMIT_BTN)
            page.wait_for_url("*joinhandshake.com/stu*", timeout=60_000)
            logger.info("Handshake login successful")

        page.wait_for_load_state("networkidle", timeout=self._settings.page_timeout_ms)

    def scrape_page(self, page: Page) -> list[JobPosting]:
        try:
            page.wait_for_selector(SEL_JOB_CARD, timeout=self._settings.page_timeout_ms)
        except PlaywrightTimeoutError:
            logger.warning("No Handshake job cards found on page")
            return []

        cards = page.query_selector_all(SEL_JOB_CARD)
        jobs = []
        for card in cards:
            try:
                link_el = card.query_selector("a")
                href = (link_el.get_attribute("href") or "") if link_el else ""
                # Extract job ID from URL pattern /jobs/12345678
                import re

                m = re.search(r"/jobs/(\d+)", href)
                posting_id = m.group(1) if m else ""

                if not posting_id:
                    continue

                jobs.append(
                    JobPosting(
                        posting_id=posting_id,
                        title=self.safe_text(card, SEL_TITLE),
                        employer=self.safe_text(card, SEL_EMPLOYER),
                        location=self.safe_text(card, SEL_LOCATION),
                        portal_url=self.absolute_url(href),
                        source_adapter=self.ADAPTER_ID,
                    )
                )
            except Exception as exc:
                logger.warning("Handshake card parse error: {}", exc)

        return jobs

    def next_page(self, page: Page) -> bool:
        btn = page.query_selector(SEL_NEXT_PAGE)
        if not btn or not btn.is_enabled():
            return False
        btn.click()
        page.wait_for_load_state("networkidle", timeout=self._settings.page_timeout_ms)
        return True


register_adapter(HandshakeAdapter)
