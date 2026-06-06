# Adapter Authoring Guide

This guide explains how to add support for a new job portal in ~30 minutes.

---

## Concepts

An **adapter** is a single Python file that knows how to:
1. Log into one specific job portal
2. Extract job postings from the portal's HTML
3. Paginate through all result pages

Everything else — scheduling, DB persistence, Telegram delivery, filtering —
is handled by the core system.

---

## Step-by-Step

### 1. Create the file

```bash
touch src/job_sentinel/adapters/sites/my_portal.py
```

### 2. Implement the interface

```python
from __future__ import annotations

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.adapters.registry import register_adapter
from job_sentinel.config.settings import ScraperSettings
from job_sentinel.core.models import JobPosting

# ── CSS Selectors ─────────────────────────────────────────────────────────────
# Define all selectors here so they're easy to update when the portal changes.
SEL_JOB_CARD = ".job-card, [data-job-id]"
SEL_TITLE    = "h3.title, .job-title"
SEL_EMPLOYER = ".company, .employer"
SEL_LOCATION = ".location"
SEL_NEXT_BTN = "button[aria-label='Next']"


class MyPortalAdapter(SiteAdapter):
    """Scraper for My Portal (myportal.com)."""

    ADAPTER_ID   = "my_portal"       # unique slug; used in SITE_ADAPTER env var
    ADAPTER_NAME = "My Portal"
    BASE_URL     = "https://myportal.com"

    def login(self, page: Page) -> None:
        """Navigate to the portal and authenticate."""
        from job_sentinel.config.settings import get_settings
        s = get_settings()

        page.goto(s.portal.jobs_url, wait_until="domcontentloaded")

        # If redirected to a login page:
        if "login" in page.url or "signin" in page.url:
            logger.info("Login page detected")
            page.fill("input[name='email']", s.portal.username)
            page.fill("input[type='password']", s.portal.password)
            page.click("button[type='submit']")
            page.wait_for_url("*myportal.com*", timeout=60_000)

        # Wait for SPA to render
        page.wait_for_load_state("networkidle", timeout=self._settings.page_timeout_ms)

    def scrape_page(self, page: Page) -> list[JobPosting]:
        """Extract job postings from the current page."""
        try:
            page.wait_for_selector(SEL_JOB_CARD, timeout=self._settings.page_timeout_ms)
        except PlaywrightTimeoutError:
            logger.warning("No job cards found on page")
            return []

        cards = page.query_selector_all(SEL_JOB_CARD)
        jobs = []

        for card in cards:
            try:
                # Extract the unique posting ID
                posting_id = card.get_attribute("data-job-id") or ""
                if not posting_id:
                    continue

                # Build a JobPosting — only posting_id is strictly required
                jobs.append(JobPosting(
                    posting_id=posting_id,
                    title=self.safe_text(card, SEL_TITLE),
                    employer=self.safe_text(card, SEL_EMPLOYER),
                    location=self.safe_text(card, SEL_LOCATION),
                    portal_url=self.absolute_url(
                        self.safe_attr(card, "a", "href")
                    ),
                    source_adapter=self.ADAPTER_ID,
                ))
            except Exception as exc:
                logger.warning("Card parse error: {}", exc)

        return jobs

    def next_page(self, page: Page) -> bool:
        """Click next page button if available. Return True if navigated."""
        btn = page.query_selector(SEL_NEXT_BTN)
        if not btn or not btn.is_enabled():
            return False
        btn.click()
        page.wait_for_load_state("networkidle", timeout=self._settings.page_timeout_ms)
        return True


# ── Self-register ─────────────────────────────────────────────────────────────
register_adapter(MyPortalAdapter)
```

### 3. Register in the registry

In `src/job_sentinel/adapters/registry.py`, add:

```python
_BUILTIN_ADAPTERS = {
    "12twenty":  "job_sentinel.adapters.sites.twelve_twenty",
    "handshake": "job_sentinel.adapters.sites.handshake",
    "my_portal": "job_sentinel.adapters.sites.my_portal",   # ← add this
}
```

### 4. Configure

In your `.env`:
```
SITE_ADAPTER=my_portal
PORTAL_JOBS_URL=https://myportal.com/jobs
PORTAL_USERNAME=your_login
PORTAL_PASSWORD=your_password
```

### 5. Test it

```bash
# Dry run — no Telegram messages
uv run job-sentinel scrape

# See what the browser does (non-headless)
HEADLESS=false uv run job-sentinel scrape
```

---

## Debugging Tips

**Browser not finding elements?**
```bash
HEADLESS=false BROWSER_SLOWMO_MS=500 uv run job-sentinel scrape
```
This opens a real browser window and slows Playwright down so you can see
exactly what's happening.

**Finding the right selectors?**
1. Open the portal in Chrome
2. Right-click a job card → Inspect
3. Look for `data-*` attributes — they're most stable across DOM changes
4. Use CSS class names only as fallback (they change with frontend redeployments)

**Portal uses SSO / Shibboleth?**
Override `login()` to handle the IdP redirect chain.  See the 12twenty adapter
as an example of CAS SSO handling.

---

## Base class helpers available to you

| Helper | Use |
|---|---|
| `self.safe_text(element, selector)` | Get inner_text() safely — never raises |
| `self.safe_attr(element, selector, attr)` | Get attribute safely |
| `self.absolute_url(href)` | Resolve relative href against BASE_URL |
| `self._settings` | `ScraperSettings` instance |
| `self._log` | loguru logger bound with `adapter=ADAPTER_ID` |

---

## Sharing your adapter

Open a PR with:
- Your adapter file in `src/job_sentinel/adapters/sites/`
- Entry in `_BUILTIN_ADAPTERS` in `registry.py`
- Tests in `tests/unit/test_adapters/test_<your_adapter>.py`
- Short description in CHANGELOG.md under `[Unreleased]`

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full PR process.
