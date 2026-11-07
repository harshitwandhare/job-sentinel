"""
sources/simplify.py
───────────────────
Source for the community-maintained internship and new-grad lists published
as GitHub READMEs (SimplifyJobs / Pitt CSC and friends).

Those lists are the fastest public feed of campus-recruiting postings: a
volunteer opens a pull request within hours of a requisition appearing, so a
role usually lands here days before it reaches an aggregator's API.

The README is one big HTML table per section.  Each ``<tr>`` holds five cells
(company, role, location, apply links, age), and a repeated company is written
as ``↳`` so the parser carries the previous name forward.  Rows whose apply
cell carries a lock marker are closed and skipped.

Nothing here is authoritative about eligibility — the list's own flags go stale
in both directions.  ``core.eligibility`` re-reads each posting from the board
that actually serves it.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from job_sentinel.sources.base import JobSource

if TYPE_CHECKING:
    from job_sentinel.core.models import JobPosting
    from job_sentinel.sources.base import JobQuery

__all__ = ["SimplifySource"]

# ── Known lists ───────────────────────────────────────────────────────────────

#: Slug → README raw URL.  Add a line to follow another season's list.
LISTS: dict[str, str] = {
    "summer2027": (
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md"
    ),
    "summer2026": (
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
    ),
    "newgrad": ("https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md"),
}

DEFAULT_LISTS: tuple[str, ...] = ("summer2027",)

# ── Parsing ───────────────────────────────────────────────────────────────────

_ROW = re.compile(r"<tr>\s*(.*?)\s*</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_APPLY = re.compile(r'href="([^"]+?)[?&]utm_source=Simplify')
_AGE = re.compile(r"(\d+)\s*(d|mo)\b")
_CARRY = "↳"
_CLOSED = ("🔒", "Closed")

#: Rough day counts so "3mo" sorts sensibly against "5d".
_UNIT_DAYS = {"d": 1, "mo": 30}


def _text(cell: str) -> str:
    """Flatten one table cell to plain text, keeping multi-line values readable."""
    cell = re.sub(r"<br\s*/?>", "; ", cell)
    cell = re.sub(r"<[^>]+>", "", cell)
    return re.sub(r"\s+", " ", html.unescape(cell)).strip()


def _age_days(cell: str) -> int | None:
    """Return the posting's age in days, or None when the cell is unparseable."""
    match = _AGE.search(cell)
    if not match:
        return None
    return int(match.group(1)) * _UNIT_DAYS[match.group(2)]


# ── Source ────────────────────────────────────────────────────────────────────


class SimplifySource(JobSource):
    """Read one or more Simplify-style GitHub lists and map the rows to postings."""

    SOURCE_ID = "simplify"
    LABEL = "Simplify GitHub lists"
    requires_key = False
    is_scraper = False
    default_enabled = True
    homepage = "https://github.com/SimplifyJobs/Summer2027-Internships"

    def __init__(self, lists: tuple[str, ...] = DEFAULT_LISTS) -> None:
        """Track *lists* by slug; unknown slugs are dropped with a warning."""
        self.lists = tuple(slug for slug in lists if slug in LISTS)
        for slug in lists:
            if slug not in LISTS:
                logger.warning("simplify: unknown list {!r}, skipping", slug)

    # ── Public interface ──────────────────────────────────────────────────────

    def search(self, query: JobQuery) -> list[JobPosting]:
        """Return postings from every configured list, newest first."""
        rows: list[tuple[int, JobPosting]] = []
        for slug in self.lists:
            try:
                rows.extend(self._read_list(slug))
            except (httpx.HTTPError, OSError) as exc:
                logger.warning("simplify: list {} unavailable: {}", slug, exc)

        rows.sort(key=lambda pair: pair[0])
        postings = [posting for age, posting in rows if self._matches(query, age, posting)]
        return postings[: query.limit] if query.limit else postings

    def health_check(self) -> bool:
        """True when the first configured list responds to a HEAD request."""
        if not self.lists:
            return False
        try:
            with self._client(timeout=5.0) as client:
                return client.head(LISTS[self.lists[0]]).status_code < 400
        except httpx.HTTPError:
            return False

    # ── Internals ─────────────────────────────────────────────────────────────

    def _read_list(self, slug: str) -> list[tuple[int, JobPosting]]:
        """Fetch one README and return (age_days, posting) pairs for its open rows."""
        with self._client(timeout=30.0) as client:
            body = client.get(LISTS[slug]).raise_for_status().text

        out: list[tuple[int, JobPosting]] = []
        employer = ""
        for row in _ROW.findall(body):
            cells = _CELL.findall(row)
            if len(cells) < 5:
                continue

            name = _text(cells[0]).replace("🔥", "").strip()
            if name and name != _CARRY:
                employer = name
            if not employer:
                continue

            apply_cell = cells[3]
            if any(marker in apply_cell for marker in _CLOSED):
                continue
            link = _APPLY.search(apply_cell)
            if not link:
                continue

            age = _age_days(cells[4])
            if age is None:
                continue

            url = link.group(1)
            out.append(
                (
                    age,
                    self._posting(
                        native_id=f"{slug}:{url}",
                        title=_text(cells[1]).replace("🎓", "").strip(),
                        employer=employer,
                        location=_text(cells[2]),
                        job_type="internship" if slug != "newgrad" else "full_time",
                        posted_date=self._posted_on(age),
                        apply_url=url,
                        is_remote="remote" in _text(cells[2]).lower(),
                        extra={"list": slug, "age_days": age},
                    ),
                )
            )
        logger.info("simplify: {} open rows from {}", len(out), slug)
        return out

    @staticmethod
    def _posted_on(age_days: int) -> str:
        """Convert an age in days to an ISO date the rest of the app can sort on."""
        return (datetime.now(UTC) - timedelta(days=age_days)).date().isoformat()

    @staticmethod
    def _matches(query: JobQuery, age_days: int, posting: JobPosting) -> bool:
        """Apply the portable query filters this source can honour."""
        if query.date_posted_days is not None and age_days > query.date_posted_days:
            return False
        if query.remote is not None and bool(posting.raw_data.get("is_remote")) != query.remote:
            return False
        if query.company and query.company.lower() not in posting.employer.lower():
            return False
        if query.location and query.location.lower() not in posting.location.lower():
            return False
        if query.keywords:
            haystack = f"{posting.title} {posting.employer}".lower()
            if not all(word in haystack for word in query.keywords.lower().split()):
                return False
        return True
