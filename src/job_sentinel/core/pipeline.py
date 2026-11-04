"""
core/pipeline.py
────────────────
One run of the apply loop: find, screen, queue.

The pieces existed separately already. A source aggregator returns postings, an
eligibility screen says whether a posting is worth the twenty minutes, and the
tracker remembers what has been seen. This ties them into one call so a session
can say "find the latest and queue what I can actually apply to" and get back
something it can act on without re-deriving anything.

Three things it will not do:

* **Decide for the user.** A blocked posting is dropped from the queue but the
  reason is kept, quoted from the posting itself, so a wrong screen is visible
  rather than silent.
* **Re-queue what was seen.** Deduplication is on the posting URL against every
  application already tracked, in any stage, so a rejection does not come back
  next week as a fresh lead.
* **Apply.** The queue is a list of saved applications. Filling and submitting
  stay with the browser filler and the user.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

from job_sentinel.core.eligibility import Status, Verdict, screen_url
from job_sentinel.core.models import Application, ApplicationStage
from job_sentinel.sources.registry import build_enabled_sources
from job_sentinel.sources.search import aggregate_search

if TYPE_CHECKING:
    from job_sentinel.config.settings import Settings
    from job_sentinel.core.models import JobPosting
    from job_sentinel.db.repository import JobRepository
    from job_sentinel.sources.base import JobQuery, JobSource

__all__ = [
    "FILLED_AT",
    "RunReport",
    "Screened",
    "find_jobs",
    "is_filled",
    "mark_filled",
    "next_to_fill",
    "queue_jobs",
    "run_find",
    "screen_jobs",
]

#: Stamped on an application once a form has been prefilled for it.
#: Not a stage: the application has not been submitted, and only the user
#: can do that. It exists so a run of several postings moves on instead of
#: handing back the same one.
FILLED_AT = "filled_at"

#: Screening is almost entirely network wait, so run a few at once. Kept low
#: on purpose: boards rate-limit, and NVIDIA's Workday starts returning 403
#: after a burst of reads from one address.
_SCREEN_WORKERS = 4


@dataclass
class Screened:
    """A posting with the verdict its own board's text produced."""

    posting: JobPosting
    verdict: Verdict

    @property
    def eligible(self) -> bool:
        """True when nothing in the posting rules the user out.

        An unreadable posting counts as eligible: a board that times out is not
        evidence of an exclusion, and dropping it would quietly hide roles.
        """
        return self.verdict.status is not Status.BLOCKED


@dataclass
class RunReport:
    """What one pass of the loop did, in the order it happened."""

    found: int = 0
    screened: int = 0
    blocked: list[Screened] = field(default_factory=list)
    duplicates: int = 0
    queued: list[Application] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        """One line for a CLI row or a chat reply."""
        return (
            f"{self.found} found, {self.screened} screened, "
            f"{len(self.blocked)} blocked, {self.duplicates} already tracked, "
            f"{len(self.queued)} queued"
        )


def find_jobs(
    query: JobQuery,
    settings: Settings,
    sources: list[JobSource] | None = None,
) -> tuple[list[JobPosting], list[str], dict[str, int]]:
    """Search every enabled source and return postings, errors and per-source counts."""
    active = sources if sources is not None else build_enabled_sources(settings)
    response = aggregate_search(query, active)
    errors = [f"{e.source}: {e.detail}" for e in response.errors]
    return list(response.results), errors, dict(response.counts)


def screen_jobs(postings: list[JobPosting], *, timeout: float = 30.0) -> list[Screened]:
    """Re-read each posting through its own board and screen the text.

    Postings without a URL are returned unscreened rather than dropped: the
    user may still want them, and a missing link is not an exclusion.
    """
    if not postings:
        return []

    def one(posting: JobPosting) -> Screened:
        if not posting.portal_url:
            return Screened(posting, Verdict(Status.UNKNOWN, detail="no URL on the posting"))
        return Screened(posting, screen_url(posting.portal_url, timeout=timeout))

    with ThreadPoolExecutor(max_workers=_SCREEN_WORKERS) as pool:
        return list(pool.map(one, postings))


def queue_jobs(screened: list[Screened], repo: JobRepository) -> tuple[list[Application], int]:
    """Save eligible postings as tracked applications. Returns (queued, duplicates).

    A posting already tracked in any stage is skipped, so a role that was
    rejected or archived does not reappear as a new lead.
    """
    known = {a.url.strip().lower() for a in repo.list_applications(limit=10_000) if a.url}
    queued: list[Application] = []
    duplicates = 0

    for item in screened:
        url = item.posting.portal_url.strip()
        if url and url.lower() in known:
            duplicates += 1
            continue
        app = Application(
            title=item.posting.title,
            employer=item.posting.employer,
            location=item.posting.location,
            url=url,
            source=item.posting.source_adapter,
            stage=ApplicationStage.SAVED,
            deadline=item.posting.deadline,
            posting_id=item.posting.posting_id,
            notes=f"Screened: {item.verdict.summary}",
            raw_data={
                "eligibility": {
                    "status": str(item.verdict.status),
                    "summary": item.verdict.summary,
                    "cautions": [explain for explain, _ in item.verdict.cautions],
                    "source": item.verdict.source,
                },
            },
        )
        repo.create_application(app)
        queued.append(app)
        if url:
            known.add(url.lower())

    return queued, duplicates


def run_find(
    query: JobQuery,
    settings: Settings,
    repo: JobRepository,
    *,
    sources: list[JobSource] | None = None,
    screen: bool = True,
    timeout: float = 30.0,
) -> RunReport:
    """Find, screen and queue in one pass.

    ``screen=False`` skips the per-posting board read, which is the slow part,
    for when the caller only wants to see what is out there.
    """
    postings, errors, counts = find_jobs(query, settings, sources)
    logger.info("apply run: {} postings from {} sources", len(postings), len(counts))

    if screen:
        results = screen_jobs(postings, timeout=timeout)
    else:
        results = [Screened(p, Verdict(Status.UNKNOWN, detail="not screened")) for p in postings]

    eligible = [r for r in results if r.eligible]
    blocked = [r for r in results if not r.eligible]
    queued, duplicates = queue_jobs(eligible, repo)

    return RunReport(
        found=len(postings),
        screened=len(results) if screen else 0,
        blocked=blocked,
        duplicates=duplicates,
        queued=queued,
        errors=errors,
        counts=counts,
    )


def is_filled(app: Application) -> bool:
    """True when a form has already been prefilled for this application."""
    return bool(app.raw_data.get(FILLED_AT))


def mark_filled(app_id: str, repo: JobRepository) -> Application | None:
    """Stamp an application as prefilled, leaving its stage alone.

    The stage stays ``saved`` because nothing has been submitted. Moving it to
    ``applied`` here would record an application the user never sent.
    """
    app = repo.get_application(app_id)
    if app is None:
        return None
    raw = dict(app.raw_data)
    raw[FILLED_AT] = datetime.now(tz=UTC).isoformat()
    repo.update_application(app_id, raw_data=raw)
    return repo.get_application(app_id)


def next_to_fill(repo: JobRepository) -> Application | None:
    """The oldest queued application that has not been prefilled yet."""
    saved = repo.list_applications(stage=ApplicationStage.SAVED, limit=500)
    pending = [a for a in saved if not is_filled(a)]
    return pending[-1] if pending else None
