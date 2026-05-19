"""
core/models.py
──────────────
Core domain models for Job Sentinel.

All data flowing through the system — scraper → db → bot → notifier —
is typed as **pydantic v2** models.  This gives us:

  • Automatic validation and coercion at every boundary
  • JSON serialise / deserialise with ``model.model_dump_json()``
  • IDE autocompletion throughout the codebase
  • A clear, self-documenting API contract

Design note — why Pydantic v2 here instead of plain dataclasses?
  The scraper pulls raw strings from HTML.  Pydantic's validators let us
  normalise dates, strip whitespace, and enforce constraints at the point
  of construction rather than scattered across scraper + db + bot code.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class ApplicationStatus(StrEnum):
    """
    Lifecycle stages of a job posting from the user's perspective.

    String values are stored verbatim in SQLite so the DB is
    human-readable with any external viewer.

    State machine:
        NEW → SEEN → APPLIED
              SEEN → IGNORED
        any  → CLOSED  (portal removed it)
    """

    NEW = "new"  # Just discovered; alert not yet sent
    SEEN = "seen"  # Alert sent via Telegram
    APPLIED = "applied"  # User marked as applied (/applied command)
    IGNORED = "ignored"  # User dismissed (/ignore command)
    CLOSED = "closed"  # No longer visible on the portal


# ─────────────────────────────────────────────────────────────────────────────
# Core domain model
# ─────────────────────────────────────────────────────────────────────────────


class JobPosting(BaseModel):
    """
    A single job posting scraped from a portal.

    Attributes
    ----------
    posting_id : str
        Unique identifier from the portal (primary key in our DB).
    title : str
        Job / position title.
    employer : str
        Company or department name.
    location : str
        Work location (city, "Remote", etc.).
    job_type : str
        e.g. "Full-Time", "Part-Time", "On-Campus".
    posted_date : str
        Date string as shown on the portal.
    deadline : str
        Application deadline (empty if not listed).
    description_snippet : str
        First ~350 characters of the job description.
    portal_url : str
        Direct link to this posting on the portal.
    status : ApplicationStatus
        Tracking lifecycle status.
    discovered_at : datetime
        UTC timestamp when the scraper first found this posting.
    updated_at : datetime
        UTC timestamp of the most recent status change.
    keywords_matched : list[str]
        Which keyword filters matched this posting.
    source_adapter : str
        The adapter ID that produced this record (e.g. "12twenty").
    raw_data : dict
        Catch-all for extra fields; stored as JSON in SQLite.
    """

    posting_id: str = Field(..., min_length=1, description="Portal-assigned unique ID")
    title: str = Field(default="Untitled Position", description="Job title")
    employer: str = Field(default="", description="Employer / department name")
    location: str = Field(default="", description="Work location")
    job_type: str = Field(default="", description="Employment type")
    posted_date: str = Field(default="", description="Date posted (as shown on portal)")
    deadline: str = Field(default="", description="Application deadline")
    description_snippet: str = Field(default="", max_length=500, description="Short description")
    portal_url: str = Field(default="", description="Direct URL to this posting")
    status: ApplicationStatus = Field(default=ApplicationStatus.NEW)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    keywords_matched: list[str] = Field(default_factory=list)
    source_adapter: str = Field(default="", description="Adapter that produced this record")
    raw_data: dict[str, Any] = Field(default_factory=dict)

    # ── Validators ────────────────────────────────────────────────────────

    @field_validator("title", "employer", "location", "job_type", mode="before")
    @classmethod
    def strip_whitespace(cls, v: object) -> str:
        return str(v).strip() if v else ""

    @field_validator("description_snippet", mode="before")
    @classmethod
    def truncate_snippet(cls, v: object) -> str:
        raw = str(v).strip() if v else ""
        return raw[:350] + "…" if len(raw) > 350 else raw

    # ── Business logic ────────────────────────────────────────────────────

    def matches_keywords(self, keywords: list[str]) -> bool:
        """
        Return ``True`` if any keyword (case-insensitive) matches the
        title, employer, job_type, or description_snippet.

        Side-effect: updates ``self.keywords_matched`` with the hits.
        Calling with an empty list always returns ``True`` (no filter).
        """
        if not keywords:
            return True

        haystack = " ".join(
            [
                self.title,
                self.employer,
                self.job_type,
                self.description_snippet,
            ]
        ).lower()

        hits = [kw for kw in keywords if kw.lower() in haystack]
        # pydantic v2 models are immutable by default — use object.__setattr__
        object.__setattr__(self, "keywords_matched", hits)
        return bool(hits)

    def touch(self) -> None:
        """Update ``updated_at`` to now (UTC)."""
        object.__setattr__(self, "updated_at", datetime.now(tz=UTC))

    def __str__(self) -> str:
        return (
            f"JobPosting(id={self.posting_id!r}, "
            f"title={self.title!r}, "
            f"employer={self.employer!r}, "
            f"status={self.status.value})"
        )

    model_config = {"frozen": False}  # allow touch() mutations


# ─────────────────────────────────────────────────────────────────────────────
# Supporting value objects
# ─────────────────────────────────────────────────────────────────────────────


class ScrapeResult(BaseModel):
    """
    Aggregated outcome of a single scrape cycle.

    Returned by the scheduler and used for logging / Telegram summaries.
    """

    adapter: str
    total_scraped: int = 0
    new_count: int = 0
    updated_count: int = 0
    closed_count: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def had_errors(self) -> bool:
        return bool(self.errors)

    def __str__(self) -> str:
        return (
            f"ScrapeResult(adapter={self.adapter}, "
            f"total={self.total_scraped}, new={self.new_count}, "
            f"errors={len(self.errors)})"
        )
