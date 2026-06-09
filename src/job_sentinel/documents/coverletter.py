"""
documents/coverletter.py
─────────────────────────
Generate a cover letter from the universal profile + a job description.

The deterministic path assembles a competent, truthful letter from the profile
(summary, most-relevant experience, top skills) — it always works with no model.
The optional ``use_ai`` path asks a *local* Ollama model to polish that draft into
smoother prose, under the same no-fabrication contract as the résumé tailor: it
may only rephrase facts already present, never invent new ones. On any failure it
falls back to the deterministic draft.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from loguru import logger

from job_sentinel.documents.tailor import KeywordTailor

if TYPE_CHECKING:
    from job_sentinel.documents.llm import OllamaClient
    from job_sentinel.profile.models import Profile

_LLM_SYSTEM = (
    "You are a professional cover-letter editor. Rewrite the provided draft "
    "paragraphs into a polished, concise, confident cover letter aligned with the "
    "job. Hard rules: use ONLY facts present in the draft/profile — never invent "
    "employers, titles, dates, metrics, or skills; keep it to 3-4 short paragraphs; "
    'no greeting or sign-off lines. Return strict JSON: {"paragraphs": ["...", ...]}.'
)


def compose_cover_letter(
    profile: Profile,
    *,
    role: str = "",
    company: str = "",
    job_description: str = "",
) -> list[str]:
    """Build truthful cover-letter body paragraphs from the profile (no model)."""
    role_phrase = role or "the role you've advertised"
    company_phrase = company or "your team"

    paragraphs: list[str] = []

    intro = f"I am writing to express my strong interest in {role_phrase} at {company_phrase}."
    if profile.basics.summary:
        intro += f" {profile.basics.summary}"
    paragraphs.append(intro)

    # Lead with the most relevant experience for this posting.
    experience = profile.experience
    if job_description and experience:
        experience = KeywordTailor().tailor(profile, job_description).profile.experience
    if experience:
        x = experience[0]
        body = f"Most recently, as {x.role} at {x.company}, "
        if x.bullets:
            first = x.bullets[0].rstrip(".")
            body += f"{first[0].lower()}{first[1:]}."
        else:
            body += "I delivered work that maps closely to what this role needs."
        paragraphs.append(body)

    if profile.skills and profile.skills[0].skills:
        top = ", ".join(profile.skills[0].skills[:6])
        paragraphs.append(
            f"I bring hands-on experience with {top}, and I pick up new tools and domains quickly."
        )

    paragraphs.append(
        "I would welcome the chance to discuss how I can contribute. Thank you for "
        "your time and consideration."
    )
    return paragraphs


def cover_letter_paragraphs(
    profile: Profile,
    *,
    role: str = "",
    company: str = "",
    job_description: str = "",
    client: OllamaClient | None = None,
) -> list[str]:
    """Deterministic draft, optionally polished by a local LLM (graceful fallback)."""
    draft = compose_cover_letter(
        profile, role=role, company=company, job_description=job_description
    )
    if client is None or not client.available() or not client.has_model():
        return draft

    user = json.dumps({"job": job_description[:2000], "draft": draft})
    try:
        data = client.chat_json(_LLM_SYSTEM, user)
        polished = data.get("paragraphs")
        if (
            isinstance(polished, list)
            and polished
            and all(isinstance(p, str) and p.strip() for p in polished)
        ):
            return [p.strip() for p in polished]
        logger.warning("LLM returned malformed cover letter — using the draft")
    except Exception as exc:
        logger.warning("LLM cover-letter polish failed ({}); using the draft", exc)
    return draft
