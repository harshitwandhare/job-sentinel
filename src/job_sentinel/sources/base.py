"""
sources/base.py
───────────────
Abstract base for all job sources and shared value objects.

A JobSource is a lightweight HTTP/JSON client (NOT a Playwright browser
adapter).  Sources search public or semi-public job APIs and return
results mapped onto the existing JobPosting domain model — ephemeral,
never written to the database.

To author a new source:
  1. Subclass JobSource in sources/<name>.py
  2. Set the class-level constants (SOURCE_ID, LABEL, …)
  3. Implement search(query) → list[JobPosting]
  4. Add the ID to _BUILTIN_SOURCES in sources/registry.py
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from job_sentinel.core.models import ApplicationStatus, JobPosting

__all__ = ["JobPosting", "JobQuery", "JobSource", "SourceError"]

# ─────────────────────────────────────────────────────────────────────────────
# Query model
# ─────────────────────────────────────────────────────────────────────────────


class JobQuery(BaseModel):
    """
    Portable search query passed to every JobSource.

    Sources use what they support and silently ignore the rest.

    Attributes
    ----------
    keywords : str
        Free-text search string (job title, skill, etc.).
    location : str
        City, region, or country string.
    remote : bool | None
        True = remote only; False = on-site only; None = no filter.
    job_type : str
        e.g. "full_time", "part_time", "contract", "internship".
    salary_min : int | None
        Minimum annual salary in USD (or source-native currency).
    date_posted_days : int | None
        Restrict to postings within the last N days.
    radius_km : int | None
        Distance from the location (sources that support geo-radius).
    seniority : str
        e.g. "junior", "mid", "senior", "lead".
    company : str
        Filter by company name (sources that support it).
    limit : int
        Max results to return from this query (per-source cap applied too).
    """

    keywords: str = ""
    location: str = ""
    remote: bool | None = None
    job_type: str = ""
    salary_min: int | None = None
    date_posted_days: int | None = None
    radius_km: int | None = None
    seniority: str = ""
    company: str = ""
    limit: int = 50


# ─────────────────────────────────────────────────────────────────────────────
# Error record
# ─────────────────────────────────────────────────────────────────────────────


class SourceError(BaseModel):
    """One per failed source — captured so the other sources still return."""

    source: str
    detail: str


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────────────────────────────────────


class JobSource(ABC):
    """
    Abstract base for all job sources.

    Subclasses only need to implement:
      - Class-level constants (SOURCE_ID, LABEL, …)
      - search(query) → list[JobPosting]
      - Optionally: health_check() → bool

    The protected _posting() helper builds a correctly shaped JobPosting
    from the common fields every source has.
    """

    # ── Class-level constants (set by each subclass) ──────────────────────────

    #: Unique slug used in the registry and as a prefix for posting_id
    SOURCE_ID: str = ""

    #: Human-readable label shown in the UI and CLI
    LABEL: str = ""

    #: Whether a user-supplied API key is mandatory for this source
    requires_key: bool = False

    #: True when this source scrapes HTML/JS rather than hitting an API
    is_scraper: bool = False

    #: True → included in the default enabled_sources list
    default_enabled: bool = False

    #: Home page / docs URL shown to the user
    homepage: str = ""

    # ── Configuration ─────────────────────────────────────────────────────────

    def configured(self) -> bool:
        """Return True when the source is ready to make requests.

        Default: always True unless requires_key is True and the subclass
        has not received a key.  Subclasses with keys should override.
        """
        return True

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def search(self, query: JobQuery) -> list[JobPosting]:
        """Search for jobs matching *query*.

        Parameters
        ----------
        query:
            The search parameters. Sources use what they support and
            silently ignore the rest.

        Returns
        -------
        list[JobPosting]
            Zero or more results. Must not raise — catch source-level
            errors internally and return [].
        """

    def health_check(self) -> bool:
        """Lightweight probe: is the source reachable?

        Default implementation always returns True.  Override for sources
        that expose a status / ping endpoint.
        """
        return True

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _posting(
        self,
        *,
        native_id: str,
        title: str,
        employer: str,
        location: str = "",
        job_type: str = "",
        posted_date: str = "",
        deadline: str = "",
        description_snippet: str = "",
        apply_url: str = "",
        salary_text: str = "",
        is_remote: bool = False,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> JobPosting:
        """
        Build a JobPosting from common fields.

        Automatically sets:
          - posting_id  = "<SOURCE_ID>:<native_id>"
          - source_adapter = SOURCE_ID
          - portal_url  = apply_url
          - status      = NEW
          - raw_data    = {salary_text, is_remote, tags, …extra}

        All string fields are stripped; missing values default gracefully.
        """
        raw: dict[str, Any] = {}
        if salary_text:
            raw["salary_text"] = salary_text
        if is_remote:
            raw["is_remote"] = True
        if tags:
            raw["tags"] = tags
        if extra:
            raw.update(extra)

        safe_id = (native_id or uuid.uuid4().hex).strip()

        return JobPosting(
            posting_id=f"{self.SOURCE_ID}:{safe_id}",
            title=title or "Untitled Position",
            employer=employer or "",
            location=location or "",
            job_type=job_type or "",
            posted_date=posted_date or "",
            deadline=deadline or "",
            description_snippet=description_snippet or "",
            portal_url=apply_url or "",
            status=ApplicationStatus.NEW,
            source_adapter=self.SOURCE_ID,
            raw_data=raw,
        )

    # ── httpx factory ─────────────────────────────────────────────────────────

    @staticmethod
    def _client(timeout: float = 10.0) -> httpx.Client:
        """Return a synchronous httpx.Client with sane defaults."""
        return httpx.Client(timeout=timeout, follow_redirects=True)
