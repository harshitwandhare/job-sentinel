"""
sources/himalayas.py
─────────────────────
JobSource for Himalayas (https://himalayas.app).

Free public API — no key required.  Remote-only jobs.
Max 20 results per request.  Supports keywords, country, and seniority.

Endpoint: GET https://himalayas.app/jobs/api/search?q=&country=&seniority=
"""

from __future__ import annotations

from loguru import logger

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource


class HimalayasSource(JobSource):
    """Himalayas remote-jobs API — no key, max 20 per request."""

    SOURCE_ID = "himalayas"
    LABEL = "Himalayas"
    requires_key = False
    is_scraper = False
    default_enabled = True
    homepage = "https://himalayas.app/jobs"

    _API_URL = "https://himalayas.app/jobs/api/search"

    def search(self, query: JobQuery) -> list[JobPosting]:
        params: dict[str, str | int] = {}
        if query.keywords:
            params["q"] = query.keywords
        if query.location:
            params["country"] = query.location
        if query.seniority:
            params["seniority"] = query.seniority

        try:
            with self._client() as client:
                resp = client.get(self._API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("himalayas: fetch failed — {}", exc)
            return []

        jobs_raw = data.get("jobs") or []
        results: list[JobPosting] = []

        for item in jobs_raw:
            # Build salary text from whatever fields exist
            salary_parts: list[str] = []
            sal_min = item.get("salaryMin") or item.get("salary_min")
            sal_max = item.get("salaryMax") or item.get("salary_max")
            currency = item.get("currency") or item.get("salaryCurrency") or ""
            if sal_min or sal_max:
                lo = f"{sal_min:,}" if sal_min else "?"
                hi = f"{sal_max:,}" if sal_max else "?"
                salary_parts.append(f"{currency} {lo}–{hi}".strip())
            salary_text = " ".join(salary_parts)

            company = item.get("company") or {}
            employer = company.get("name", "") if isinstance(company, dict) else str(company)

            posting = self._posting(
                native_id=str(item.get("id", "") or item.get("slug", "")),
                title=item.get("title", ""),
                employer=employer,
                location="Worldwide",
                job_type=item.get("jobType", "") or "",
                posted_date=item.get("createdAt", "") or "",
                apply_url=item.get("applicationLink", "") or item.get("url", ""),
                description_snippet=item.get("description", "") or "",
                salary_text=salary_text,
                is_remote=True,
            )
            results.append(posting)
            if len(results) >= query.limit:
                break

        return results
