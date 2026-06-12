"""
adapters/sites/twelve_twenty.py
────────────────────────────────
Site adapter for **12twenty** portals (UTD and other universities).

12twenty is an AngularJS single-page app. The listing view fetches its data
from an internal JSON API (``POST /Api/V2/job-postings/post-query``), so the
most reliable scrape strategy is:

  1. Reuse the session captured by ``job-sentinel login`` (the login page is
     behind a Cloudflare Turnstile challenge, so headless form login rarely
     gets through — but we attempt it as a fallback, prefilled from .env).
  2. Attach a response listener for the post-query API *before* navigating.
  3. Navigate to the listings URL; the SPA fires the query and we capture the
     structured JSON (title, employer, deadline, applicant count, …).
  4. Scroll the table to trigger lazy-loaded pages — each one fires another
     post-query we also capture.
  5. If for any reason no API traffic was seen, fall back to DOM parsing of
     the rendered ``tr.job-posting`` rows.

URL hygiene
───────────
A ``viewId=<n>`` in the configured jobs URL refers to a *saved search view*.
If that view doesn't belong to the logged-in account, 12twenty responds
"Sorry! You are not authorized to make this request." and renders an empty
table — which historically made the scraper report "done 0" with a perfectly
valid session. We therefore strip ``viewId`` from the URL before navigating.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from loguru import logger
from playwright.sync_api import Page, Response
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from job_sentinel.adapters.base import SessionStatus, SiteAdapter
from job_sentinel.adapters.registry import register_adapter
from job_sentinel.core.models import JobPosting

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, ElementHandle

    from job_sentinel.config.settings import ScraperSettings

# ─────────────────────────────────────────────────────────────────────────────
# Portal constants
# ─────────────────────────────────────────────────────────────────────────────

PORTAL_BASE_URL = "https://utdallas.12twenty.com"

# Internal JSON endpoints (verified against live UTD traffic, 2026-06).
API_POST_QUERY = "/job-postings/post-query"  # matched as a URL substring
API_CURRENT_USER = "/api/v2/account/current-user"
API_POSTING_DETAIL = "/Api/V2/job-postings/{posting_id}"  # full side-modal payload

# Be polite to the portal when fetching per-posting details.
DETAIL_FETCH_DELAY_MS = 150

# ── Login form (12twenty's own email/password form — no SSO) ─────────────────
SEL_EMAIL = "input[type='email'], input[name='email'], input#email, input[name='username']"
SEL_PASSWORD = "input[type='password'], input#password"  # noqa: S105 — selector, not a secret
SEL_LOGIN_BTN = "button[type='submit'], input[type='submit']"

# ── Authenticated app shell ───────────────────────────────────────────────────
# The side navigation renders on every authenticated page, even when the job
# table is empty — so it is the reliable "logged in" signal (the old
# row-based selector reported false negatives on empty lists and false
# positives on the login shell). Verified against the live DOM (2026-06):
# the nav is #side-nav with .side-nav-link entries and an a.logout item.
SEL_APP_SHELL = "#side-nav a.side-nav-link, a.logout"
# One combined wait — whichever of these appears first tells us where we are.
SEL_SHELL_OR_LOGIN = f"{SEL_APP_SHELL}, input[type='password']"

# ── Listing rows (DOM fallback when no API traffic was captured) ─────────────
SEL_JOB_CARD = "tr.job-posting"
SEL_TITLE_LINK = "a.job-title"
SEL_JOB_TITLE = "a.job-title .primary-item-text"
SEL_EMPLOYER = "span.sub-info:not(:has(span.sub-info-item))"
SEL_SUB_ITEM = "span.sub-info-item"
SEL_DEADLINE = "tt-date-time-display"

# ── "Not authorized" modal (defensive: dismiss it if it ever appears) ────────
SEL_MODAL_OK = ".modal-dialog button, .sweet-alert button.confirm, button:has-text('OK')"

# Posting id lives in the title href: …#/jobPostings/<digits>
_POSTING_ID_RE = re.compile(r"/jobPostings/(\d+)")
# "5 days ago", "1 week ago", "today", "yesterday" — relative posted date.
_POSTED_RE = re.compile(r"\b(ago|today|yesterday)\b", re.IGNORECASE)
# viewId=<n> inside the hash fragment (see "URL hygiene" above).
_VIEW_ID_RE = re.compile(r"viewId=\d+&?")


def sanitize_jobs_url(url: str) -> str:
    """Strip a ``viewId`` saved-search reference that can 403 for this account."""
    cleaned = _VIEW_ID_RE.sub("", url)
    return cleaned.rstrip("?&")


class TwelveTwentyAdapter(SiteAdapter):
    """
    Scraper for 12twenty job portals (UTD Student Employment and others).

    Configured via:
      - ``PORTAL_JOBS_URL``  — the full URL to the listings tab
      - ``PORTAL_USERNAME``  — portal email
      - ``PORTAL_PASSWORD``  — portal password
    """

    ADAPTER_ID = "12twenty"
    ADAPTER_NAME = "12twenty Portal"
    BASE_URL = PORTAL_BASE_URL
    LOGGED_IN_SELECTOR = SEL_APP_SHELL
    LOGIN_EMAIL_SELECTOR = SEL_EMAIL
    LOGIN_PASSWORD_SELECTOR = SEL_PASSWORD

    def __init__(self, scraper_settings: ScraperSettings) -> None:
        super().__init__(scraper_settings)
        self._jobs_url: str = ""  # set from portal settings at scrape time
        self._api_items: dict[str, dict[str, Any]] = {}  # posting id → raw API item

    # ── Session check ──────────────────────────────────────────────────────

    def check_session(self, context: BrowserContext) -> SessionStatus:
        """Cheap session probe: hit the current-user API with the stored cookies."""
        try:
            resp = context.request.get(f"{self.BASE_URL}{API_CURRENT_USER}", timeout=15_000)
            if resp.ok:
                data = resp.json()
                name = ""
                if isinstance(data, dict):
                    name = str(
                        data.get("FullName")
                        or data.get("FirstName", "")
                        or data.get("EmailAddress", "")
                    ).strip()
                return SessionStatus(valid=True, user=name)
            return SessionStatus(valid=False, detail=f"HTTP {resp.status}")
        except Exception as exc:
            return SessionStatus(valid=False, detail=str(exc))

    # ── Login ──────────────────────────────────────────────────────────────

    def login(self, page: Page) -> None:
        """
        Reach the authenticated job-listings view.

        Preferred path: a session saved by ``job-sentinel login`` is already
        loaded into the browser context, so navigating straight to the jobs URL
        renders the listing. If we land on the login form instead (session
        expired), we attempt a direct email/password submit — but the live
        login page is Cloudflare-gated, so that fallback often won't get
        through; the user should re-run ``job-sentinel login`` in that case.
        """
        from job_sentinel.config.settings import get_settings  # lazy import

        settings = get_settings()
        self._jobs_url = sanitize_jobs_url(settings.portal.jobs_url)
        timeout = self._settings.page_timeout_ms

        # Capture the structured job data the SPA fetches while it renders.
        self._api_items.clear()
        page.on("response", self._capture_post_query)

        logger.info("Navigating to portal | url={}", self._jobs_url)
        page.goto(self._jobs_url, wait_until="domcontentloaded")

        # Wait until either the authenticated app shell or a login form renders.
        try:
            page.wait_for_selector(SEL_SHELL_OR_LOGIN, timeout=timeout)
        except PlaywrightTimeoutError:
            logger.debug("Neither app shell nor login form rendered in time")

        if page.query_selector(SEL_APP_SHELL):
            logger.debug("Session active — authenticated app shell rendered")
            self._dismiss_error_modal(page)
            return

        email = page.query_selector(SEL_EMAIL)
        pwd = page.query_selector(SEL_PASSWORD)
        if email and pwd:
            logger.info("Login form detected — submitting credentials from .env")
            email.fill(settings.portal.username)
            pwd.fill(settings.portal.password)
            btn = page.query_selector(SEL_LOGIN_BTN)
            if btn:
                btn.click()
            else:
                pwd.press("Enter")
            page.wait_for_selector(SEL_APP_SHELL, timeout=timeout)
            self._dismiss_error_modal(page)
        else:
            msg = (
                "Session expired and the login form is unreachable (the 12twenty "
                "login sits behind a Cloudflare challenge). Run `job-sentinel login` "
                "or use the dashboard's Login button to sign in once."
            )
            raise RuntimeError(msg)

    # ── Page scraping ──────────────────────────────────────────────────────

    def scrape_page(self, page: Page) -> list[JobPosting]:
        """
        Collect every posting: scroll to force all lazy pages of the API query,
        then parse from the captured JSON (preferred) or the DOM (fallback).
        """
        # Wait for either rendered rows or the API to have answered.
        try:
            page.wait_for_selector(SEL_JOB_CARD, timeout=self._settings.page_timeout_ms)
        except PlaywrightTimeoutError:
            if not self._api_items:
                logger.warning(
                    "No job rows and no API data — the list may be empty for this account"
                )
                return []

        self._load_all_rows(page)

        if self._api_items:
            jobs = [
                job
                for item in self._api_items.values()
                if (job := self._job_from_api(item)) is not None
            ]
            logger.info("Parsed {} postings from the 12twenty API", len(jobs))
            self._enrich_with_details(page, jobs)
            return jobs

        # DOM fallback — selectors verified against the live UTD DOM (2026-06).
        cards = page.query_selector_all(SEL_JOB_CARD)
        logger.info("API capture empty — parsing {} DOM rows instead", len(cards))
        return [job for card in cards if (job := self._parse_card(card, page)) is not None]

    def next_page(self, page: Page) -> bool:
        """
        12twenty has no numbered pager — everything for a search lives in one
        lazily-extended table that :meth:`scrape_page` already exhausts via
        scrolling. So there is never a "next page" to advance to.
        """
        return False

    # ── API capture ──────────────────────────────────────────────────────────

    def _capture_post_query(self, response: Response) -> None:
        """Response listener: harvest job items from every post-query call."""
        if API_POST_QUERY not in response.url or response.status != 200:
            return
        try:
            body = response.json()
        except Exception:
            return
        items = body.get("Items") if isinstance(body, dict) else None
        if not isinstance(items, list):
            return
        for item in items:
            posting_id = str(item.get("Id", "")).strip()
            if posting_id:
                self._api_items[posting_id] = item
        logger.debug(
            "Captured post-query page | items={} total_unique={}",
            len(items),
            len(self._api_items),
        )

    def _job_from_api(self, item: dict[str, Any]) -> JobPosting | None:
        """Map one post-query API item onto our JobPosting model."""
        try:
            posting_id = str(item["Id"])
            raw = {
                "api": True,
                "num_applicants": item.get("NumApplicants"),
                "application_status": item.get("ApplicationStatusDisplay"),
                "is_applied": item.get("IsApplied"),
                "status_name": item.get("StatusName"),
                "company_id": item.get("CompanyId"),
            }
            return JobPosting(
                posting_id=posting_id,
                title=item.get("TitleDisplay") or item.get("JobTitle") or "Untitled Position",
                employer=item.get("CompanyName") or "",
                location=item.get("LocationDisplay") or "",
                job_type=item.get("JobPostingJobTypeNames") or "",
                posted_date=_format_iso_date(item.get("PostedDate")),
                deadline=_format_iso_date(item.get("ApplicationDeadlineDate")),
                portal_url=f"{self.BASE_URL}/jobPostings#/jobPostings/{posting_id}",
                source_adapter=self.ADAPTER_ID,
                raw_data=raw,
            )
        except Exception as exc:
            logger.warning("Failed to map API item: {} | item={}", exc, json.dumps(item)[:200])
            return None

    # ── Detail enrichment (the side-modal payload) ──────────────────────────

    def _enrich_with_details(self, page: Page, jobs: list[JobPosting]) -> None:
        """
        Fetch each posting's full record (description, salary, contact, …)
        from the same REST endpoint the side modal uses, and attach it.
        """
        request = page.context.request
        enriched = 0
        for job in jobs:
            url = f"{self.BASE_URL}{API_POSTING_DETAIL.format(posting_id=job.posting_id)}"
            try:
                resp = request.get(url, timeout=15_000)
                if not resp.ok:
                    logger.debug("Detail fetch HTTP {} | id={}", resp.status, job.posting_id)
                    continue
                detail = resp.json()
            except Exception as exc:
                logger.debug("Detail fetch failed | id={} err={}", job.posting_id, exc)
                continue

            description = _strip_html(str(detail.get("Description") or ""))
            # Truncate by hand — assignment bypasses the model's "before" validator.
            job.description_snippet = (
                description[:350] + "…" if len(description) > 350 else description
            )
            job.raw_data["detail"] = _summarise_detail(detail, description)
            enriched += 1
            page.wait_for_timeout(DETAIL_FETCH_DELAY_MS)
        logger.info("Enriched {}/{} postings with full details", enriched, len(jobs))

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _dismiss_error_modal(page: Page) -> None:
        """Close a 'not authorized' popup if one is blocking the view."""
        try:
            body = page.inner_text("body", timeout=3_000)
        except Exception:
            return
        if "not authorized" not in body.lower():
            return
        logger.warning("Portal showed a 'not authorized' popup — dismissing it")
        btn = page.query_selector(SEL_MODAL_OK)
        if btn:
            try:
                btn.click()
                page.wait_for_timeout(500)
            except Exception as exc:
                logger.debug("Modal dismiss click failed (continuing): {}", exc)

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
                    timeout=2_500,
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


def _format_iso_date(value: object) -> str:
    """'2026-08-17T13:00:00' → '2026-08-17' (keep raw string if unparsable)."""
    if not value:
        return ""
    text = str(value)
    return text.split("T")[0] if "T" in text else text


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]*\n[ \t]*\n[\s]*")


def _strip_html(html: str) -> str:
    """Plain-text-ify the rich-text Description field."""
    text = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", html, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    # Unescape the handful of entities 12twenty actually emits.
    for entity, char in (
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&#39;", "'"),
        ("&quot;", '"'),
    ):
        text = text.replace(entity, char)
    return _WS_RE.sub("\n\n", text).strip()


def _join_names(seq: object) -> str:
    """Join the display names from a list of lookup dicts, skipping null names."""
    if not isinstance(seq, list):
        return ""
    names = []
    for entry in seq:
        if isinstance(entry, dict):
            name = entry.get("Name") or entry.get("DisplayName")
            if name:
                names.append(str(name))
    return ", ".join(names)


def _summarise_detail(detail: dict[str, Any], description: str) -> dict[str, Any]:
    """Curate the side-modal fields worth keeping out of the ~150-key payload."""
    salary = ""
    base = detail.get("BaseSalary")
    if base:
        currency = detail.get("CurrencyName") or "USD"
        fmt = detail.get("PayFormatName") or ""
        salary = f"{base} {currency} {fmt}".strip()
    documents = [
        f"{d.get('DocumentTypeName')}{' (Required)' if d.get('IsRequired') else ' (Optional)'}"
        for d in detail.get("JobPostingApplicationDocumentTypes") or []
        if isinstance(d, dict) and d.get("DocumentTypeName")
    ]
    return {
        "description": description,
        "salary": salary,
        "salary_min": detail.get("SalaryMin"),
        "salary_max": detail.get("SalaryMax"),
        "openings": detail.get("NumberAccepted") or detail.get("NumOtherSlots"),
        "industry": _join_names(detail.get("Industries")),
        "job_function": _join_names(detail.get("Functions")),
        "work_study_required": detail.get("IsWorkStudyRequired"),
        "application_begins": detail.get("ApplicationStartDate"),
        "job_start_date": detail.get("JobStartDate"),
        "application_documents": documents,
        "contact_name": detail.get("ContactName"),
        "contact_title": detail.get("ContactJobTitle"),
        "contact_email": detail.get("ContactEmail"),
        "apply_via_site": detail.get("ShouldApplyViaSite"),
        "external_url": detail.get("Url"),
        "num_applicants": detail.get("NumApplicants"),
        "required_work_auth": detail.get("RequiredWorkAuthName"),
        "time_commitment": detail.get("JobTimeCommitmentName"),
    }


# ── Self-register when this module is imported ────────────────────────────────
register_adapter(TwelveTwentyAdapter)
