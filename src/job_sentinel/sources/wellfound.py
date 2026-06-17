"""
sources/wellfound.py
─────────────────────
JobSource for Wellfound (https://wellfound.com) — formerly AngelList Talent.

Uses the public GraphQL API that powers the search page.  No API key required
for read-only job searches; unauthenticated requests return the same listing
data visible to logged-out visitors.

Focus: startup / tech roles, strong on early-stage and remote positions.
"""

from __future__ import annotations

import re

from loguru import logger

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource

_GQL_URL = "https://wellfound.com/graphql"

# Minimal GraphQL query — mirrors what the job search page sends.
_JOB_SEARCH_QUERY = """
query JobSearchResults($query: String, $locationFilter: String, $remote: Boolean, $page: Int) {
  jobListings(
    query: $query
    locationFilter: $locationFilter
    remote: $remote
    page: $page
  ) {
    startups {
      name
      twitterUrl
      jobListings {
        id
        title
        description
        jobType
        remote
        salary
        createdAt
        slug
        startupRole { url }
      }
    }
  }
}
"""


def _clean_salary(raw: object) -> str:
    if not raw:
        return ""
    text = str(raw)
    return re.sub(r"<[^>]+>", "", text).strip()


class WellfoundSource(JobSource):
    """Wellfound (formerly AngelList) public GraphQL job search."""

    SOURCE_ID = "wellfound"
    LABEL = "Wellfound"
    requires_key = False
    is_scraper = False
    default_enabled = True
    homepage = "https://wellfound.com/jobs"

    def search(self, query: JobQuery) -> list[JobPosting]:
        variables: dict[str, object] = {"page": 1}
        if query.keywords:
            variables["query"] = query.keywords
        if query.location:
            variables["locationFilter"] = query.location
        if query.remote is True:
            variables["remote"] = True

        payload = {
            "operationName": "JobSearchResults",
            "query": _JOB_SEARCH_QUERY,
            "variables": variables,
        }

        try:
            with self._client() as client:
                resp = client.post(
                    _GQL_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("wellfound: fetch failed — {}", exc)
            return []

        errors = data.get("errors")
        if errors:
            logger.warning("wellfound: GraphQL errors — {}", errors)
            return []

        job_listings_data = (data.get("data") or {}).get("jobListings") or {}
        startups: list[dict[str, object]] = (
            job_listings_data.get("startups", []) if isinstance(job_listings_data, dict) else []
        )

        results: list[JobPosting] = []
        for company in startups:
            company_name = str(company.get("name") or "")
            listings = company.get("jobListings") or []
            if not isinstance(listings, list):
                continue
            for item in listings:
                if not isinstance(item, dict):
                    continue

                role = item.get("startupRole") or {}
                apply_url = (
                    (role.get("url") if isinstance(role, dict) else None)
                    or f"https://wellfound.com/jobs/{item.get('slug', '')}"
                )

                posting = self._posting(
                    native_id=str(item.get("id") or item.get("slug") or ""),
                    title=str(item.get("title") or ""),
                    employer=company_name,
                    location="Remote" if item.get("remote") else (query.location or ""),
                    job_type=str(item.get("jobType") or ""),
                    posted_date=str(item.get("createdAt") or ""),
                    apply_url=str(apply_url),
                    description_snippet=str(item.get("description") or "")[:500],
                    salary_text=_clean_salary(item.get("salary")),
                    is_remote=bool(item.get("remote")),
                )
                results.append(posting)
                if len(results) >= query.limit:
                    return results

        return results
