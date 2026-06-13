"""
sources/remoteok.py
────────────────────
JobSource for Remote OK (https://remoteok.com).

Public JSON API — no key required.  Returns remote-only jobs.
Endpoint: GET https://remoteok.com/api

The first element of the array is API metadata; skip it.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource


class RemoteOkSource(JobSource):
    """Remote OK public API — remote jobs, no key needed."""

    SOURCE_ID = "remoteok"
    LABEL = "Remote OK"
    requires_key = False
    is_scraper = False
    default_enabled = True
    homepage = "https://remoteok.com"

    _API_URL = "https://remoteok.com/api"
    _USER_AGENT = "job-sentinel/1.0 (+https://github.com/harshitwandhare/job-sentinel)"

    def search(self, query: JobQuery) -> list[JobPosting]:
        """Fetch all jobs and filter client-side by keywords."""
        try:
            with self._client() as client:
                resp = client.get(
                    self._API_URL,
                    headers={"User-Agent": self._USER_AGENT, "Accept": "application/json"},
                )
                resp.raise_for_status()
                data: list[Any] = resp.json()
        except Exception as exc:
            logger.warning("remoteok: fetch failed — {}", exc)
            return []

        if not isinstance(data, list):
            return []

        # Skip the first element (API metadata object)
        jobs_raw = [item for item in data[1:] if isinstance(item, dict)]

        kw = query.keywords.lower()
        results: list[JobPosting] = []
        for item in jobs_raw:
            # Cheap client-side keyword filter (API has no server-side search)
            if kw:
                haystack = " ".join(
                    str(item.get(f, "")) for f in ("position", "company", "tags", "description")
                ).lower()
                if kw not in haystack:
                    continue

            tags: list[str] = item.get("tags") or []
            posting = self._posting(
                native_id=str(item.get("id", "")),
                title=item.get("position", ""),
                employer=item.get("company", ""),
                location=item.get("location", "Worldwide"),
                job_type="",
                posted_date=item.get("date", ""),
                apply_url=item.get("apply_url") or item.get("url", ""),
                description_snippet=item.get("description", ""),
                salary_text=item.get("salary", ""),
                is_remote=True,
                tags=tags if isinstance(tags, list) else [],
            )
            results.append(posting)
            if len(results) >= query.limit:
                break

        return results
