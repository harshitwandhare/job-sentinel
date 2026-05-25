"""
adapters/base.py
────────────────
Abstract base class for all site adapters.

Architecture — Plugin Pattern
──────────────────────────────
Job Sentinel is **site-agnostic**.  The scraping logic for each portal
lives in a separate ``SiteAdapter`` subclass.  The rest of the system
(scheduler, DB, notifier, bot) never imports a concrete adapter directly
— they only speak the ``SiteAdapter`` interface defined here.

This means:
  • Adding a new portal = writing one new file in ``adapters/sites/``
  • No changes to any other part of the system
  • Users can ship their own adapters without touching the core

To author an adapter, see: docs/design/adapter-authoring.md

Adapter contract
────────────────
Every adapter must:
  1. Subclass ``SiteAdapter``
  2. Set ``ADAPTER_ID`` — a unique slug (e.g. ``"12twenty"``)
  3. Implement ``login(page)`` and ``scrape_page(page) → list[JobPosting]``
  4. Optionally implement ``next_page(page) → bool``

The base class provides helpers for safe text extraction, URL building,
and a ``scrape()`` entry-point that orchestrates the full cycle.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from loguru import logger
from playwright.sync_api import (
    BrowserContext,
    ElementHandle,
    Page,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

if TYPE_CHECKING:
    from job_sentinel.config.settings import ScraperSettings
    from job_sentinel.core.models import JobPosting


class SiteAdapter(ABC):
    """
    Abstract base for all portal scrapers.

    Subclasses only need to implement:
      - ``ADAPTER_ID`` (class-level string)
      - ``login(page)``
      - ``scrape_page(page) → list[JobPosting]``
      - ``next_page(page) → bool``  (optional — default returns False)

    The ``scrape(context)`` method is provided here and should not be
    overridden unless the site has a very unusual flow.
    """

    # ── Class-level constants (set by each subclass) ─────────────────────

    #: Unique identifier registered in the adapter registry
    ADAPTER_ID: str = ""

    #: Human-readable name shown in logs and Telegram messages
    ADAPTER_NAME: str = ""

    #: Base URL of the portal (used for building absolute URLs)
    BASE_URL: str = ""

    # ── Constructor ───────────────────────────────────────────────────────

    def __init__(self, scraper_settings: ScraperSettings) -> None:
        self._settings = scraper_settings
        self._log = logger.bind(adapter=self.ADAPTER_ID)

    # ── Abstract interface (must be implemented by each site) ─────────────

    @abstractmethod
    def login(self, page: Page) -> None:
        """
        Navigate to the portal and complete any authentication flow.

        After this method returns, ``page`` must be on the job-listings
        page and the session must be authenticated.

        Parameters
        ----------
        page:
            A fresh Playwright page created by the caller.
        """

    @abstractmethod
    def scrape_page(self, page: Page) -> list[JobPosting]:
        """
        Extract all job postings visible on the current page state.

        Called once per page after login and after each pagination step.

        Parameters
        ----------
        page:
            Playwright page already navigated to a listings page.

        Returns
        -------
        list[JobPosting]
            Postings found on this page (may be empty).
        """

    def next_page(self, page: Page) -> bool:
        """
        Navigate to the next results page if one exists.

        Default implementation returns ``False`` (single-page portals).
        Override for portals with pagination.

        Returns
        -------
        bool
            ``True`` if navigation to the next page succeeded,
            ``False`` if we're on the last page.
        """
        return False

    # ── Orchestrator (provided — override only if needed) ─────────────────

    def scrape(self, context: BrowserContext) -> list[JobPosting]:
        """
        Full scrape cycle: login → paginate → collect all postings.

        Orchestrates ``login`` → ``scrape_page`` → ``next_page`` in a loop.
        Catches Playwright timeouts and logs them without propagating.

        Parameters
        ----------
        context:
            A Playwright ``BrowserContext`` (manages cookies / session).

        Returns
        -------
        list[JobPosting]
            All postings found across all pages.
        """
        all_jobs: list[JobPosting] = []
        page = context.new_page()
        page.set_default_timeout(self._settings.page_timeout_ms)

        try:
            self._log.info("Starting scrape | adapter={}", self.ADAPTER_ID)
            self.login(page)

            page_num = 0
            while page_num < self._settings.max_pages:
                page_num += 1
                self._log.debug("Scraping page {}", page_num)

                try:
                    jobs = self.scrape_page(page)
                except PlaywrightTimeoutError as exc:
                    self._log.warning("Timeout on page {} — {}", page_num, exc)
                    break

                all_jobs.extend(jobs)
                self._log.debug("Page {} → {} jobs", page_num, len(jobs))

                if not self.next_page(page):
                    self._log.debug("No next page — stopping at page {}", page_num)
                    break

                # Brief pause between pages — polite scraping
                time.sleep(0.8)

            self._log.info("Scrape complete | total_jobs={}", len(all_jobs))

        except PlaywrightTimeoutError as exc:
            self._log.error("Playwright timeout during login/scrape: {}", exc)
        except Exception as exc:
            self._log.exception("Unexpected error during scrape: {}", exc)
        finally:
            page.close()

        return all_jobs

    # ── Shared helpers (available to all subclasses) ───────────────────────

    def absolute_url(self, href: str) -> str:
        """Resolve a relative href against the adapter's BASE_URL."""
        if not href:
            return self.BASE_URL
        return href if href.startswith("http") else urljoin(self.BASE_URL, href)

    @staticmethod
    def safe_text(element: ElementHandle, selector: str) -> str:
        """
        Query ``selector`` inside ``element`` and return inner_text().

        Returns empty string on any failure — never raises.
        """
        try:
            el = element.query_selector(selector)
            return el.inner_text().strip() if el else ""
        except Exception:
            return ""

    @staticmethod
    def safe_attr(element: ElementHandle, selector: str, attr: str) -> str:
        """
        Query ``selector`` inside ``element`` and return an attribute value.

        Returns empty string on any failure — never raises.
        """
        try:
            el = element.query_selector(selector)
            return (el.get_attribute(attr) or "").strip() if el else ""
        except Exception:
            return ""
