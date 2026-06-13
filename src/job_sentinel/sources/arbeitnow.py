"""
sources/arbeitnow.py
─────────────────────
JobSource for Arbeitnow (https://www.arbeitnow.com).

Free, open JSON API — no key required.  Supports remote flag, job_types,
and visa sponsorship filter.

Endpoint: GET https://www.arbeitnow.com/api/job-board-api
"""

from __future__ import annotations

from loguru import logger

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource


class ArbeitnowSource(JobSource):
    """Arbeitnow free job board API — EU-focused, no key needed."""

    SOURCE_ID = "arbeitnow"
    LABEL = "Arbeitnow"
    requires_key = False
    is_scraper = False
    default_enabled = True
    homepage = "https://www.arbeitnow.com"

    _API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def search(self, query: JobQuery) -> list[JobPosting]:
        params: dict[str, str | int | bool] = {}
        if query.remote is True:
            params["remote"] = "true"
        if query.job_type:
            params["job_types[]"] = query.job_type

        try:
            with self._client() as client:
                resp = client.get(self._API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("arbeitnow: fetch failed — {}", exc)
            return []

        jobs_raw = data.get("data") or []
        kw = query.keywords.lower()
        results: list[JobPosting] = []

        for item in jobs_raw:
            if kw:
                haystack = " ".join(
                    [
                        item.get("title", ""),
                        item.get("company_name", ""),
                        item.get("description", ""),
                        " ".join(item.get("tags") or []),
                    ]
                ).lower()
                if kw not in haystack:
                    continue

            tags = item.get("tags") or []
            posting = self._posting(
                native_id=item.get("slug", ""),
                title=item.get("title", ""),
                employer=item.get("company_name", ""),
                location=item.get("location", ""),
                job_type=", ".join(item.get("job_types") or []),
                posted_date=str(item.get("created_at", "")),
                apply_url=item.get("url", ""),
                description_snippet=item.get("description", ""),
                is_remote=bool(item.get("remote", False)),
                tags=tags if isinstance(tags, list) else [],
                extra={"visa_sponsorship": item.get("visa_sponsorship", False)},
            )
            results.append(posting)
            if len(results) >= query.limit:
                break

        return results
