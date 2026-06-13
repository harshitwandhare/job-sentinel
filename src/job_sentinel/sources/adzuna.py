"""
sources/adzuna.py
──────────────────
JobSource for Adzuna (https://developer.adzuna.com).

Requires a free user key: ADZUNA_APP_ID + ADZUNA_APP_KEY.
Supports real salary ranges and geo-radius filtering.
Country defaults to "us" (ADZUNA_COUNTRY).

Endpoint:
  GET https://api.adzuna.com/v1/api/jobs/{country}/search/1
      ?app_id=…&app_key=…&what=…&where=…&distance=…&salary_min=…
"""

from __future__ import annotations

from loguru import logger

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource


class AdzunaSource(JobSource):
    """Adzuna job search API — requires free ADZUNA_APP_ID + ADZUNA_APP_KEY."""

    SOURCE_ID = "adzuna"
    LABEL = "Adzuna"
    requires_key = True
    is_scraper = False
    default_enabled = False
    homepage = "https://developer.adzuna.com"

    _API_BASE = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, app_id: str = "", app_key: str = "", country: str = "us") -> None:
        self._app_id = app_id
        self._app_key = app_key
        self._country = country or "us"

    def configured(self) -> bool:
        return bool(self._app_id and self._app_key)

    def search(self, query: JobQuery) -> list[JobPosting]:
        if not self.configured():
            logger.warning("adzuna: ADZUNA_APP_ID / ADZUNA_APP_KEY not set — skipping")
            return []

        url = f"{self._API_BASE}/{self._country}/search/1"
        params: dict[str, str | int] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "results_per_page": min(query.limit, 50),
            "what": query.keywords,
        }
        if query.location:
            params["where"] = query.location
        if query.salary_min is not None:
            params["salary_min"] = query.salary_min
        if query.radius_km is not None:
            # Adzuna expects distance in km
            params["distance"] = query.radius_km

        try:
            with self._client() as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("adzuna: fetch failed — {}", exc)
            return []

        results: list[JobPosting] = []
        for item in data.get("results") or []:
            sal_min = item.get("salary_min")
            sal_max = item.get("salary_max")
            salary_text = ""
            if sal_min or sal_max:
                lo = f"${sal_min:,.0f}" if sal_min else "?"
                hi = f"${sal_max:,.0f}" if sal_max else "?"
                salary_text = f"{lo}–{hi}/yr"

            loc = item.get("location") or {}
            area = loc.get("area") or []
            loc_str = ", ".join(str(a) for a in area if a) if isinstance(area, list) else ""

            posting = self._posting(
                native_id=str(item.get("id", "")),
                title=item.get("title", ""),
                employer=(item.get("company") or {}).get("display_name", ""),
                location=loc_str or query.location,
                job_type=item.get("contract_type", "") or "",
                posted_date=item.get("created", ""),
                apply_url=item.get("redirect_url", ""),
                description_snippet=item.get("description", ""),
                salary_text=salary_text,
            )
            results.append(posting)
            if len(results) >= query.limit:
                break

        return results
