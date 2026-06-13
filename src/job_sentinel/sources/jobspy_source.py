"""
sources/jobspy_source.py
─────────────────────────
Opt-in scraper backend powered by python-jobspy.

INSTALL:  pip install job-sentinel[sources]

TOS_WARNING
───────────
JobSpy scrapes job boards including Indeed, ZipRecruiter, Glassdoor,
and Google Jobs. Scraping may violate those sites' Terms of Service.
By using this source you accept full responsibility for compliance with
the target sites' ToS.  LinkedIn is explicitly excluded from the default
sites list because of the hiQ Labs v. LinkedIn Corp ruling and ongoing
enforcement.  The owner of job-sentinel assumes no liability.

Configure via environment variables:
  JOBSPY_SITES   Comma-separated list of sites (default: indeed,zip_recruiter,glassdoor,google)
  JOBSPY_COUNTRY Country code (default: USA)
  JOBSPY_PROXIES Comma-separated list of proxy URLs
"""

from __future__ import annotations

import os
from typing import Any

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource

TOS_WARNING = (
    "JobSpy scrapes job boards. This may violate target-site Terms of Service. "
    "LinkedIn is excluded by default (ref: hiQ Labs v. LinkedIn Corp). "
    "You assume all legal responsibility for use of this source."
)

_DEFAULT_SITES = ["indeed", "zip_recruiter", "glassdoor", "google"]


class JobSpySource(JobSource):
    """
    Opt-in scraper via python-jobspy.

    Install:  pip install job-sentinel[sources]

    Scrapes Indeed, ZipRecruiter, Glassdoor, and Google Jobs by default.
    LinkedIn is intentionally omitted — see TOS_WARNING above.
    """

    SOURCE_ID = "jobspy"
    LABEL = "JobSpy (scraper)"
    requires_key = False
    is_scraper = True
    default_enabled = False
    homepage = "https://github.com/Bunsly/JobSpy"

    def _get_sites(self) -> list[str]:
        raw = os.environ.get("JOBSPY_SITES", "")
        if raw:
            return [s.strip() for s in raw.split(",") if s.strip()]
        return list(_DEFAULT_SITES)

    def _get_country(self) -> str:
        return os.environ.get("JOBSPY_COUNTRY", "USA")

    def _get_proxies(self) -> list[str]:
        raw = os.environ.get("JOBSPY_PROXIES", "")
        if raw:
            return [p.strip() for p in raw.split(",") if p.strip()]
        return []

    def search(self, query: JobQuery) -> list[JobPosting]:
        try:
            from jobspy import scrape_jobs
        except ImportError as exc:
            msg = (
                "JobSpy is not installed. "
                "Run: pip install job-sentinel[sources]\n"
                "Or: pip install python-jobspy>=1.1.79"
            )
            raise RuntimeError(msg) from exc

        kwargs: dict[str, Any] = {
            "site_name": self._get_sites(),
            "search_term": query.keywords,
            "results_wanted": min(query.limit, 50),
            "country_indeed": self._get_country(),
        }
        if query.location:
            kwargs["location"] = query.location
        proxies = self._get_proxies()
        if proxies:
            kwargs["proxies"] = proxies
        if query.job_type:
            kwargs["job_type"] = query.job_type

        try:
            df = scrape_jobs(**kwargs)
        except Exception as exc:
            from loguru import logger

            logger.warning("jobspy: scrape_jobs failed — {}", exc)
            return []

        results: list[JobPosting] = []
        for _, row in df.iterrows():
            job_url = str(row.get("job_url") or "")
            native_id = str(row.get("id") or job_url or "")

            sal_min = row.get("min_amount")
            sal_max = row.get("max_amount")
            currency = row.get("currency") or ""
            interval = row.get("interval") or ""
            salary_text = ""
            if sal_min or sal_max:
                lo = f"{sal_min:,.0f}" if sal_min else "?"
                hi = f"{sal_max:,.0f}" if sal_max else "?"
                salary_text = f"{currency} {lo}–{hi} {interval}".strip()

            is_remote = bool(row.get("is_remote") or False)
            date_val = row.get("date_posted")
            posted = str(date_val) if date_val else ""

            posting = self._posting(
                native_id=native_id,
                title=str(row.get("title") or ""),
                employer=str(row.get("company") or ""),
                location=str(row.get("location") or ""),
                job_type=str(row.get("job_type") or ""),
                posted_date=posted,
                apply_url=job_url,
                description_snippet=str(row.get("description") or "")[:350],
                salary_text=salary_text,
                is_remote=is_remote,
                extra={"source_site": str(row.get("site") or "")},
            )
            results.append(posting)
            if len(results) >= query.limit:
                break

        return results
