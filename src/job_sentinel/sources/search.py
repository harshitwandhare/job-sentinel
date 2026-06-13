"""
sources/search.py
──────────────────
Aggregate search across multiple JobSources.

Results are:
  - Collected concurrently (ThreadPoolExecutor — sources are sync)
  - Per-source failures are captured as SourceError (other sources continue)
  - Deduplicated by (title, employer) pair and exact portal_url
  - Sorted newest-first when a parseable date exists
  - Capped to query.limit total results
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from job_sentinel.sources.base import JobQuery, JobSource, SourceError

# ─────────────────────────────────────────────────────────────────────────────
# Response model
# ─────────────────────────────────────────────────────────────────────────────


class SearchResponse(BaseModel):
    """Aggregate result returned by aggregate_search."""

    results: list[Any]  # list[JobPosting] — Any avoids circular import issues
    errors: list[SourceError]
    counts: dict[str, int]  # source_id → result count from that source


# ─────────────────────────────────────────────────────────────────────────────
# Date parsing helper
# ─────────────────────────────────────────────────────────────────────────────

_ISO_PAT = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _parse_date(date_str: str) -> datetime | None:
    """Extract an ISO date substring and parse it; return None on failure."""
    if not date_str:
        return None
    m = _ISO_PAT.search(date_str)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Core aggregation
# ─────────────────────────────────────────────────────────────────────────────


def aggregate_search(
    query: JobQuery,
    sources: list[JobSource],
) -> SearchResponse:
    """
    Search all *sources* concurrently and return an aggregated result.

    Parameters
    ----------
    query:
        The search parameters passed to every source.
    sources:
        List of instantiated JobSource objects to query.

    Returns
    -------
    SearchResponse
        Combined results, per-source errors, and per-source counts.
    """
    if not sources:
        return SearchResponse(results=[], errors=[], counts={})

    all_results: list[Any] = []
    errors: list[SourceError] = []
    counts: dict[str, int] = {}

    def _search_one(src: JobSource) -> tuple[str, list[Any], str | None]:
        """Run one source, returning (source_id, results, error_detail|None)."""
        try:
            jobs = src.search(query)
            return src.SOURCE_ID, jobs, None
        except Exception as exc:  # intentional broad catch — isolate per-source failures
            return src.SOURCE_ID, [], str(exc)

    with ThreadPoolExecutor(max_workers=min(len(sources), 8)) as pool:
        futures = {pool.submit(_search_one, src): src for src in sources}
        for future in as_completed(futures):
            sid, jobs, err = future.result()
            if err is not None:
                errors.append(SourceError(source=sid, detail=err))
                counts[sid] = 0
            else:
                counts[sid] = len(jobs)
                all_results.extend(jobs)

    # ── Deduplicate ───────────────────────────────────────────────────────────
    seen_key: set[tuple[str, str]] = set()
    seen_url: set[str] = set()
    deduped: list[Any] = []

    for job in all_results:
        title_key = job.title.lower().strip()
        employer_key = job.employer.lower().strip()
        pair = (title_key, employer_key)
        url = job.portal_url.strip()

        if pair in seen_key:
            continue
        if url and url in seen_url:
            continue

        seen_key.add(pair)
        if url:
            seen_url.add(url)
        deduped.append(job)

    # ── Sort newest-first ─────────────────────────────────────────────────────
    def _sort_key(job: Any) -> datetime:
        d = _parse_date(job.posted_date)
        return d if d is not None else datetime.min.replace(tzinfo=UTC)

    deduped.sort(key=_sort_key, reverse=True)

    # ── Cap to limit ──────────────────────────────────────────────────────────
    deduped = deduped[: query.limit]

    return SearchResponse(
        results=deduped,
        errors=errors,
        counts=counts,
    )
