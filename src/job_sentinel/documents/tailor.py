"""
documents/tailor.py
────────────────────
Tailor the universal profile to a specific job description.

This is the deterministic core: given a profile and a job description, score
every profile item by keyword overlap, reorder so the most relevant content
leads, and report ATS keyword coverage (which of the job's terms the résumé
actually contains).

It's structured around a small :class:`Tailor` Protocol so a future
local-LLM-backed tailor can drop in behind the same interface without touching
callers — the rule is: always works without the heavy/optional backend, gets
smarter with it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, Field

from job_sentinel.core.text import strip_html

# Runtime import (not TYPE_CHECKING): pydantic resolves the TailorResult.profile
# field annotation at class-creation time, so the class must exist at runtime.
from job_sentinel.profile.models import Profile  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Iterable

# Common words that carry no matching signal — kept short and dependency-free.
_STOPWORDS = frozenset(
    """
    a an the and or but if then else for to of in on at by with from as is are was were be
    been being this that these those it its we you they i he she them our your their will
    would can could should may might must do does did done have has had not no yes your you
    role roles work works working experience experiences year years month months team teams
    ability able strong excellent good great new using use used job position opportunity
    candidate candidates applicant required requirement requirements responsibilities skills
    skill including etc per via across within while during about into out over under more most
    """.split()  # noqa: SIM905 — a wrapped word list reads better than a 60-item literal
)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}")


def extract_keywords(text: str) -> set[str]:
    """Lowercased content tokens from ``text``, minus stopwords and short noise.

    HTML/URLs are stripped first so markup tokens (``href``, ``https``, ``h3``)
    from source descriptions never count as keywords.
    """
    cleaned = strip_html(text or "")
    tokens = (m.group(0).lower().strip(".-") for m in _TOKEN_RE.finditer(cleaned))
    return {t for t in tokens if len(t) >= 2 and t not in _STOPWORDS}


class TailorResult(BaseModel):
    """Outcome of tailoring: the reordered profile plus a match report."""

    profile: Profile
    score: float = Field(ge=0.0, le=1.0, description="ATS keyword coverage, 0..1")
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)

    @property
    def score_pct(self) -> int:
        return round(self.score * 100)


class Tailor(Protocol):
    """Anything that can tailor a profile to a job description."""

    def tailor(self, profile: Profile, job_description: str) -> TailorResult: ...


class KeywordTailor:
    """Deterministic, dependency-free tailor based on keyword overlap."""

    def tailor(self, profile: Profile, job_description: str) -> TailorResult:
        job_kw = extract_keywords(job_description)

        tailored = profile.model_copy(deep=True)
        if job_kw:
            tailored.experience.sort(key=lambda x: self._relevance(x, job_kw), reverse=True)
            tailored.projects.sort(key=lambda x: self._relevance(x, job_kw), reverse=True)
            tailored.skills.sort(
                key=lambda g: len(extract_keywords(" ".join(g.skills)) & job_kw), reverse=True
            )

        resume_kw = extract_keywords(self._profile_text(tailored))
        matched = sorted(job_kw & resume_kw)
        missing = sorted(job_kw - resume_kw)
        score = (len(matched) / len(job_kw)) if job_kw else 0.0
        return TailorResult(
            profile=tailored,
            score=score,
            matched_keywords=matched,
            missing_keywords=missing,
        )

    # ── internals ───────────────────────────────────────────────────────────

    @staticmethod
    def _relevance(item: object, job_kw: set[str]) -> int:
        """Overlap between an item's text + tags and the job keywords."""
        tags = {t.lower() for t in getattr(item, "tags", [])}
        text_parts: list[str] = list(tags)
        for attr in ("role", "company", "name", "description"):
            value = getattr(item, attr, "")
            if value:
                text_parts.append(str(value))
        for attr in ("bullets", "highlights"):
            text_parts.extend(getattr(item, attr, []) or [])
        return len(extract_keywords(" ".join(text_parts)) & job_kw)

    @staticmethod
    def _profile_text(profile: Profile) -> str:
        """Flatten the visible résumé text for coverage scoring."""
        parts: list[str] = [profile.basics.summary, profile.basics.headline]
        parts.extend(_iter_strings(profile))
        return " ".join(p for p in parts if p)


def _iter_strings(profile: Profile) -> Iterable[str]:
    for x in profile.experience:
        yield f"{x.role} {x.company}"
        yield from x.bullets
        yield from x.tags
    for pr in profile.projects:
        yield f"{pr.name} {pr.description}"
        yield from pr.bullets
        yield from pr.tags
    for ed in profile.education:
        yield f"{ed.institution} {ed.degree}"
        yield from ed.highlights
    for grp in profile.skills:
        yield from grp.skills
    for c in profile.certifications:
        yield c.name
