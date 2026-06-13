"""
sources/usajobs.py
───────────────────
JobSource for USAJobs (https://www.usajobs.gov).

US Federal jobs — requires a free USAJOBS_API_KEY and USAJOBS_EMAIL.
Register at: https://developer.usajobs.gov/APIRequest/Index

Endpoint: GET https://data.usajobs.gov/api/search
  Headers: Authorization-Key: <key>, User-Agent: <email>
  Params:  Keyword=, LocationName=, DatePosted=, ResultsPerPage=
"""

from __future__ import annotations

from loguru import logger

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource


class USAJobsSource(JobSource):
    """USAJobs API — US federal government positions, requires a free key."""

    SOURCE_ID = "usajobs"
    LABEL = "USAJobs"
    requires_key = True
    is_scraper = False
    default_enabled = False
    homepage = "https://www.usajobs.gov"

    _API_URL = "https://data.usajobs.gov/api/search"

    def __init__(self, api_key: str = "", email: str = "") -> None:
        self._api_key = api_key
        self._email = email

    def configured(self) -> bool:
        return bool(self._api_key and self._email)

    def search(self, query: JobQuery) -> list[JobPosting]:
        if not self.configured():
            logger.warning("usajobs: USAJOBS_API_KEY / USAJOBS_EMAIL not set — skipping")
            return []

        params: dict[str, str | int] = {
            "ResultsPerPage": min(query.limit, 50),
        }
        if query.keywords:
            params["Keyword"] = query.keywords
        if query.location:
            params["LocationName"] = query.location
        if query.date_posted_days is not None:
            params["DatePosted"] = query.date_posted_days

        headers = {
            "Authorization-Key": self._api_key,
            "User-Agent": self._email,
            "Host": "data.usajobs.gov",
        }

        try:
            with self._client() as client:
                resp = client.get(self._API_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("usajobs: fetch failed — {}", exc)
            return []

        search_result = data.get("SearchResult") or {}
        items = search_result.get("SearchResultItems") or []
        results: list[JobPosting] = []

        for item in items:
            matched = item.get("MatchedObjectDescriptor") or {}
            position_id = matched.get("PositionID", "")
            title = matched.get("PositionTitle", "")
            org = matched.get("OrganizationName", "")
            apply_url = matched.get("ApplyURI", [""])[0] if matched.get("ApplyURI") else ""

            # Location
            locs = matched.get("PositionLocation") or [{}]
            loc_str = "; ".join(
                loc.get("LocationName", "") for loc in locs if loc.get("LocationName")
            )

            # Posted date
            start_date = matched.get("PositionStartDate", "")

            # Salary
            remun = matched.get("PositionRemuneration") or [{}]
            salary_text = ""
            if remun:
                r = remun[0]
                mn = r.get("MinimumRange", "")
                mx = r.get("MaximumRange", "")
                rate = r.get("RateIntervalCode", "")
                if mn or mx:
                    salary_text = f"${mn}–${mx} {rate}".strip()

            description = matched.get("UserArea", {}).get("Details", {}).get("JobSummary", "")

            posting = self._posting(
                native_id=position_id,
                title=title,
                employer=org,
                location=loc_str,
                job_type=matched.get("PositionSchedule", [{}])[0].get("Name", "")
                if matched.get("PositionSchedule")
                else "",
                posted_date=start_date,
                apply_url=apply_url,
                description_snippet=description,
                salary_text=salary_text,
            )
            results.append(posting)
            if len(results) >= query.limit:
                break

        return results
