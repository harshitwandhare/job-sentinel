"""
sources/themuse.py
───────────────────
JobSource for The Muse (https://www.themuse.com).

Public API — works without a key (limited rate); THEMUSE_API_KEY raises
rate limit when supplied.

Endpoint: GET https://www.themuse.com/api/public/jobs?page=N&api_key=…
"""

from __future__ import annotations

from loguru import logger

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource


class TheMuseSource(JobSource):
    """The Muse public jobs API — optional THEMUSE_API_KEY raises rate limit."""

    SOURCE_ID = "themuse"
    LABEL = "The Muse"
    requires_key = False
    is_scraper = False
    default_enabled = True
    homepage = "https://www.themuse.com/jobs"

    _API_URL = "https://www.themuse.com/api/public/jobs"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def search(self, query: JobQuery) -> list[JobPosting]:
        collected: list[JobPosting] = []
        page = 0
        max_pages = 5  # safety cap

        while len(collected) < query.limit and page < max_pages:
            params: dict[str, str | int] = {"page": page, "page_size": 20}
            if self._api_key:
                params["api_key"] = self._api_key
            if query.location:
                params["location"] = query.location
            if query.seniority:
                params["level"] = query.seniority

            try:
                with self._client() as client:
                    resp = client.get(self._API_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as exc:
                logger.warning("themuse: fetch failed page={} — {}", page, exc)
                break

            results_raw = data.get("results") or []
            if not results_raw:
                break

            kw = query.keywords.lower()
            for item in results_raw:
                if kw:
                    haystack = " ".join(
                        [
                            item.get("name", ""),
                            item.get("company", {}).get("name", ""),
                            " ".join(c.get("name", "") for c in item.get("categories", [])),
                        ]
                    ).lower()
                    if kw not in haystack:
                        continue

                company = item.get("company") or {}
                locations = item.get("locations") or [{}]
                loc_str = "; ".join(loc.get("name", "") for loc in locations if loc.get("name"))
                levels = item.get("levels") or [{}]
                level_str = "; ".join(lv.get("name", "") for lv in levels if lv.get("name"))

                posting = self._posting(
                    native_id=str(item.get("id", "")),
                    title=item.get("name", ""),
                    employer=company.get("name", "") if isinstance(company, dict) else "",
                    location=loc_str,
                    job_type=level_str,
                    posted_date=item.get("publication_date", ""),
                    apply_url=item.get("refs", {}).get("landing_page", ""),
                    description_snippet=item.get("contents", "")[:350],
                )
                collected.append(posting)
                if len(collected) >= query.limit:
                    break

            # Paginate until we have enough or exhaust results
            total = data.get("total", 0)
            page += 1
            if (page * 20) >= total:
                break

        return collected
