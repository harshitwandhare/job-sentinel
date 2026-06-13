"""
sources/company_boards.py
──────────────────────────
Follow specific employers via their public ATS job boards.

Supported ATS platforms (no auth, publicly accessible):
  - Greenhouse: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
  - Lever:      https://api.lever.co/v0/postings/{slug}?mode=json
  - Ashby:      https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true

Usage — standalone helper:
    from job_sentinel.sources.company_boards import fetch_company_board
    jobs = fetch_company_board(ats="greenhouse", slug="stripe")

Usage — as a JobSource (searches all followed companies in one call):
    source = CompanyBoardSource(followed=[("greenhouse","stripe"), ("lever","linear")])
    results = source.search(query)
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource

# ─────────────────────────────────────────────────────────────────────────────
# Supported ATS slugs
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_ATS = frozenset({"greenhouse", "lever", "ashby"})


# ─────────────────────────────────────────────────────────────────────────────
# Per-ATS parsers
# ─────────────────────────────────────────────────────────────────────────────


def _parse_greenhouse(data: dict[str, Any], slug: str) -> list[JobPosting]:
    jobs: list[JobPosting] = []
    for item in data.get("jobs") or []:
        loc = item.get("location") or {}
        departments = item.get("departments") or [{}]
        dept = departments[0].get("name", "") if departments else ""

        posting = _build(
            source_id="company_board",
            native_id=f"greenhouse:{slug}:{item.get('id', '')}",
            title=item.get("title", ""),
            employer=slug,
            location=loc.get("name", "") if isinstance(loc, dict) else str(loc),
            job_type=dept,
            posted_date=item.get("updated_at", ""),
            apply_url=item.get("absolute_url", ""),
            description_snippet=(item.get("content") or "")[:350],
            extra={"ats": "greenhouse", "company_slug": slug},
        )
        jobs.append(posting)
    return jobs


def _parse_lever(data: list[Any], slug: str) -> list[JobPosting]:
    jobs: list[JobPosting] = []
    for item in data:
        categories = item.get("categories") or {}
        posting = _build(
            source_id="company_board",
            native_id=f"lever:{slug}:{item.get('id', '')}",
            title=item.get("text", ""),
            employer=slug,
            location=categories.get("location", "") if isinstance(categories, dict) else "",
            job_type=categories.get("team", "") if isinstance(categories, dict) else "",
            posted_date=str(item.get("createdAt", "")),
            apply_url=item.get("hostedUrl", ""),
            description_snippet=(item.get("descriptionPlain") or "")[:350],
            extra={"ats": "lever", "company_slug": slug},
        )
        jobs.append(posting)
    return jobs


def _parse_ashby(data: dict[str, Any], slug: str) -> list[JobPosting]:
    jobs: list[JobPosting] = []
    for item in data.get("jobPostings") or []:
        # Compensation block (optional, only when includeCompensation=true)
        comp = item.get("compensation") or {}
        salary_text = ""
        if comp:
            lo = comp.get("minValue")
            hi = comp.get("maxValue")
            curr = comp.get("currency", "")
            interval = comp.get("interval", "")
            if lo or hi:
                lo_str = f"{lo:,}" if lo else "?"
                hi_str = f"{hi:,}" if hi else "?"
                salary_text = f"{curr} {lo_str}–{hi_str} {interval}".strip()

        posting = _build(
            source_id="company_board",
            native_id=f"ashby:{slug}:{item.get('id', '')}",
            title=item.get("title", ""),
            employer=slug,
            location=item.get("locationName", "") or item.get("location", ""),
            job_type=item.get("employmentType", ""),
            posted_date=item.get("publishedDate", ""),
            apply_url=item.get("jobPostingUrl", ""),
            description_snippet=(item.get("descriptionPlain") or "")[:350],
            salary_text=salary_text,
            is_remote=bool(item.get("isRemote", False)),
            extra={"ats": "ashby", "company_slug": slug},
        )
        jobs.append(posting)
    return jobs


def _build(
    *,
    source_id: str,
    native_id: str,
    title: str,
    employer: str,
    location: str = "",
    job_type: str = "",
    posted_date: str = "",
    apply_url: str = "",
    description_snippet: str = "",
    salary_text: str = "",
    is_remote: bool = False,
    extra: dict[str, Any] | None = None,
) -> JobPosting:
    """Shared posting builder (mirrors JobSource._posting logic)."""
    from job_sentinel.core.models import ApplicationStatus

    raw: dict[str, Any] = {}
    if salary_text:
        raw["salary_text"] = salary_text
    if is_remote:
        raw["is_remote"] = True
    if extra:
        raw.update(extra)

    return JobPosting(
        posting_id=f"{source_id}:{native_id}",
        title=title or "Untitled Position",
        employer=employer or "",
        location=location or "",
        job_type=job_type or "",
        posted_date=posted_date or "",
        deadline="",
        description_snippet=description_snippet[:350] if description_snippet else "",
        portal_url=apply_url or "",
        status=ApplicationStatus.NEW,
        source_adapter=source_id,
        raw_data=raw,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public helper
# ─────────────────────────────────────────────────────────────────────────────


def fetch_company_board(ats: str, slug: str) -> list[JobPosting]:
    """
    Fetch job postings directly from a company's public ATS board.

    Parameters
    ----------
    ats:
        One of "greenhouse", "lever", or "ashby".
    slug:
        The company slug as used on the ATS (e.g. "stripe", "linear").

    Returns
    -------
    list[JobPosting]
        All current openings from that company's board.

    Raises
    ------
    ValueError
        If *ats* is not one of the supported platforms.
    """
    ats = ats.strip().lower()
    if ats not in SUPPORTED_ATS:
        msg = f"Unsupported ATS: {ats!r}. Supported: {sorted(SUPPORTED_ATS)}"
        raise ValueError(msg)

    if ats == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    elif ats == "lever":
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    else:  # ashby
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("company_boards: fetch failed ats={} slug={} — {}", ats, slug, exc)
        return []

    if ats == "greenhouse":
        return _parse_greenhouse(data, slug)
    if ats == "lever":
        return _parse_lever(data, slug)
    return _parse_ashby(data, slug)


# ─────────────────────────────────────────────────────────────────────────────
# JobSource wrapper
# ─────────────────────────────────────────────────────────────────────────────


class CompanyBoardSource(JobSource):
    """
    Search a predefined list of followed companies via their ATS boards.

    Pass ``followed`` as a list of (ats, slug) tuples, e.g.
    [("greenhouse", "stripe"), ("lever", "linear")].
    """

    SOURCE_ID = "company_board"
    LABEL = "Company ATS Boards"
    requires_key = False
    is_scraper = False
    default_enabled = False
    homepage = "https://github.com/harshitwandhare/job-sentinel"

    def __init__(self, followed: list[tuple[str, str]] | None = None) -> None:
        self._followed = followed or []

    def search(self, query: JobQuery) -> list[JobPosting]:
        results: list[JobPosting] = []
        kw = query.keywords.lower()

        for ats, slug in self._followed:
            try:
                jobs = fetch_company_board(ats, slug)
            except (ValueError, RuntimeError) as exc:
                logger.warning("company_boards: skipping {}/{} — {}", ats, slug, exc)
                continue

            for job in jobs:
                if kw:
                    haystack = f"{job.title} {job.employer} {job.description_snippet}".lower()
                    if kw not in haystack:
                        continue
                results.append(job)
                if len(results) >= query.limit:
                    return results

        return results
