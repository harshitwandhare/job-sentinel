"""
documents/match.py
───────────────────
AI-match: score how well the user's profile fits a job description.

Design
──────
Three signals are blended into a single 0..1 score:

1. **Coverage** (ATS keyword overlap) — always computed, dependency-free.
   Delegated to :class:`~job_sentinel.documents.tailor.KeywordTailor` so the
   same normalisation and stopword list is reused.

2. **Semantic** (embedding cosine similarity) — computed when the embed backend
   is available; skipped gracefully when it is not.  The whole profile is
   flattened to a single text blob and embedded alongside the JD.

3. **Rationale / strengths / gaps** (optional LLM) — when ``use_ai=True`` and
   the chat backend is ready, a single constrained JSON call grounds the
   explanation in the actual matched/missing keywords.  Falls back to a
   deterministic text if the backend is absent or returns bad JSON.

Blend
─────
- Both signals available:  ``score = 0.5 * coverage + 0.5 * semantic``
- Semantic missing:          ``score = coverage``

Verdict thresholds: ≥ 0.70 → "strong", ≥ 0.45 → "moderate", else "weak".

No fabrication contract
───────────────────────
The LLM prompt is grounded: it receives the matched/missing keyword lists and is
instructed to use ONLY facts present there.  On any validation failure the
deterministic fallback fires, so callers always get a valid :class:`MatchResult`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger
from pydantic import BaseModel, Field

from job_sentinel.config.settings import LLMSettings
from job_sentinel.documents.embeddings import cosine_similarity
from job_sentinel.documents.providers import build_chat_backend, build_embed_backend
from job_sentinel.documents.tailor import KeywordTailor

if TYPE_CHECKING:
    from job_sentinel.profile.models import Profile

# ── Verdict thresholds ────────────────────────────────────────────────────────
_STRONG = 0.70
_MODERATE = 0.45

# Number of keywords shown in the deterministic fallback strings
_FALLBACK_LIMIT = 5


class MatchResult(BaseModel):
    """Full match report for a profile vs. a job description."""

    score: float = Field(ge=0.0, le=1.0, description="Blended fit score, 0..1")
    coverage: float = Field(ge=0.0, le=1.0, description="ATS keyword coverage, 0..1")
    semantic: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Embedding cosine similarity, 0..1; None when embedder unavailable",
    )
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    verdict: str = Field(description='"strong" | "moderate" | "weak"')
    rationale: str = Field(description="2-3 sentence summary of the match")
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)

    @property
    def score_pct(self) -> int:
        """Score as a rounded percentage integer (0..100)."""
        return round(self.score * 100)


def _verdict(score: float) -> str:
    if score >= _STRONG:
        return "strong"
    if score >= _MODERATE:
        return "moderate"
    return "weak"


def _profile_text(profile: Profile) -> str:
    """Flatten the whole profile to a single string for embedding."""
    parts: list[str] = [profile.basics.name, profile.basics.headline, profile.basics.summary]
    for x in profile.experience:
        parts += [x.role, x.company, *x.bullets, *x.tags]
    for pr in profile.projects:
        parts += [pr.name, pr.description, *pr.bullets, *pr.tags]
    for ed in profile.education:
        parts += [ed.institution, ed.degree, *ed.highlights]
    for grp in profile.skills:
        parts += grp.skills
    for c in profile.certifications:
        parts.append(c.name)
    return " ".join(p for p in parts if p)


def _deterministic_rationale(
    coverage: float,
    semantic: float | None,
    matched: list[str],
    missing: list[str],
    verdict: str,
) -> tuple[str, list[str], list[str]]:
    """Build a grounded rationale without an LLM."""
    pct = round(coverage * 100)
    sem_note = ""
    if semantic is not None:
        sem_pct = round(semantic * 100)
        sem_note = f" Semantic alignment is {sem_pct}%."
    top_matched = matched[:_FALLBACK_LIMIT]
    top_missing = missing[:_FALLBACK_LIMIT]

    if verdict == "strong":
        opening = f"The profile is a strong match ({pct}% ATS keyword coverage).{sem_note}"
    elif verdict == "moderate":
        opening = f"The profile is a moderate match ({pct}% ATS keyword coverage).{sem_note}"
    else:
        opening = f"The profile is a weak match ({pct}% ATS keyword coverage).{sem_note}"

    matched_note = f" Key aligned skills include: {', '.join(top_matched)}." if top_matched else ""
    missing_note = (
        f" Skills that could close the gap: {', '.join(top_missing)}." if top_missing else ""
    )
    rationale = opening + matched_note + missing_note

    strengths = [f"Profile contains '{kw}'" for kw in top_matched]
    gaps = [f"Profile does not cover '{kw}'" for kw in top_missing]
    return rationale, strengths, gaps


_SYSTEM_PROMPT = """\
You are a career-match analyst. You ONLY use facts explicitly provided to you — \
never invent skills, experience, or details not present in the input.
Respond with a JSON object matching exactly this schema:
{
  "rationale": "<2-3 sentences summarising fit>",
  "strengths": ["<short phrase>", ...],
  "gaps": ["<short phrase>", ...]
}
Use ONLY the matched and missing keyword lists provided. Do not fabricate anything.\
"""


def _ai_rationale(
    profile: Profile,
    matched: list[str],
    missing: list[str],
    score: float,
    verdict: str,
) -> tuple[str, list[str], list[str]] | None:
    """
    Call the chat backend for a grounded rationale.

    Returns (rationale, strengths, gaps) or None on any failure.
    The caller must fall back to the deterministic version on None.
    """
    try:
        cfg = LLMSettings()
        backend = build_chat_backend(cfg)
        if not (backend.available() and backend.ready()):
            return None

        pct = round(score * 100)
        user_msg = (
            f"Candidate name: {profile.basics.name or 'unknown'}.\n"
            f"Overall match score: {pct}% ({verdict}).\n"
            f"Matched keywords (present in profile): {', '.join(matched[:20]) or 'none'}.\n"
            f"Missing keywords (absent from profile): {', '.join(missing[:20]) or 'none'}.\n"
            "Produce the JSON rationale now."
        )
        raw: dict[str, Any] = backend.chat_json(_SYSTEM_PROMPT, user_msg)
    except Exception as exc:
        logger.debug("match AI rationale failed ({}); using deterministic fallback", exc)
        return None

    # Validate shape strictly — reject on any mismatch
    try:
        rationale = str(raw["rationale"]).strip()
        strengths_raw = raw["strengths"]
        gaps_raw = raw["gaps"]
        if not rationale:
            return None
        if not isinstance(strengths_raw, list) or not isinstance(gaps_raw, list):
            return None
        strengths = [str(s) for s in strengths_raw if s]
        gaps = [str(g) for g in gaps_raw if g]
    except (KeyError, TypeError) as exc:
        logger.debug("match AI rationale: bad JSON shape ({}); using deterministic fallback", exc)
        return None

    return rationale, strengths, gaps


def _semantic_score(profile: Profile, job_description: str) -> float | None:
    """
    Compute cosine similarity between the profile blob and the JD.

    Returns a value in [0, 1] or None if the embedder is unavailable/fails.
    """
    try:
        cfg = LLMSettings()
        embedder = build_embed_backend(cfg)
        if not (embedder.available() and embedder.ready()):
            return None

        profile_blob = _profile_text(profile)
        if not profile_blob.strip():
            return None

        vectors = embedder.embed([profile_blob, job_description])
        if not vectors or len(vectors) < 2:
            return None

        sim = cosine_similarity(vectors[0], vectors[1])
        # Cosine similarity is already in [-1, 1]; clamp to [0, 1].
        return max(0.0, min(1.0, sim))
    except Exception as exc:
        logger.debug("match semantic scoring failed ({}); skipping", exc)
        return None


def match_profile_to_job(
    profile: Profile,
    job_description: str,
    *,
    use_ai: bool = True,
) -> MatchResult:
    """
    Score how well *profile* fits *job_description*.

    Parameters
    ----------
    profile:
        The universal profile to evaluate.
    job_description:
        Raw text of the job posting.
    use_ai:
        When True (default), attempt to generate a grounded LLM rationale.
        The result is always valid even when ``use_ai=False`` or the backend
        is unavailable — the deterministic fallback fires automatically.

    Returns
    -------
    MatchResult
        Always returns a complete, valid result regardless of backend availability.
    """
    # ── 1. Keyword coverage (always available) ────────────────────────────────
    tailor_result = KeywordTailor().tailor(profile, job_description)
    coverage = tailor_result.score
    matched = tailor_result.matched_keywords
    missing = tailor_result.missing_keywords

    # ── 2. Semantic similarity (optional) ────────────────────────────────────
    semantic: float | None = None
    if job_description.strip():
        semantic = _semantic_score(profile, job_description)

    # ── 3. Blend ──────────────────────────────────────────────────────────────
    blended = 0.5 * coverage + 0.5 * semantic if semantic is not None else coverage

    blended = max(0.0, min(1.0, blended))
    verd = _verdict(blended)

    # ── 4. Rationale ─────────────────────────────────────────────────────────
    rationale: str
    strengths: list[str]
    gaps: list[str]

    if use_ai:
        ai_result = _ai_rationale(profile, matched, missing, blended, verd)
        if ai_result is not None:
            rationale, strengths, gaps = ai_result
        else:
            rationale, strengths, gaps = _deterministic_rationale(
                coverage, semantic, matched, missing, verd
            )
    else:
        rationale, strengths, gaps = _deterministic_rationale(
            coverage, semantic, matched, missing, verd
        )

    return MatchResult(
        score=blended,
        coverage=coverage,
        semantic=semantic,
        matched_keywords=matched,
        missing_keywords=missing,
        verdict=verd,
        rationale=rationale,
        strengths=strengths,
        gaps=gaps,
    )
