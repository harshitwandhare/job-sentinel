"""
documents/llm.py
─────────────────
Optional LLM tailoring layer.

Supports any provider configured in ``LLMSettings`` (Ollama, OpenAI,
OpenRouter, Groq, Gemini, or a custom OpenAI-compatible endpoint) via the
backend abstraction in ``providers.py``.

Design guarantees
─────────────────
- **Always degrades gracefully.** If the configured provider isn't reachable
  or the model isn't ready, the deterministic keyword tailor is used.
- **No fabrication.** The model may only *rephrase* bullets already in the
  profile; the prompt forbids inventing employers, titles, dates, metrics, or
  technologies.  Output is JSON-validated and length-checked; any deviation
  keeps the original bullets.

Backward compatibility
──────────────────────
``OllamaClient`` is kept as a thin alias for the native ``OllamaBackend`` so
code that imported it directly (e.g. ``coverletter.py``, ``resume_import.py``)
continues to work without changes.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from job_sentinel.documents.providers import OllamaBackend
from job_sentinel.documents.tailor import KeywordTailor, TailorResult

if TYPE_CHECKING:
    from job_sentinel.documents.providers import ChatBackend
    from job_sentinel.documents.tailor import Tailor
    from job_sentinel.profile.models import Profile

_SYSTEM_PROMPT = (
    "You are a precise resume editor. Rewrite each bullet to be concise and "
    "achievement-oriented, aligned with the target job, using strong action verbs "
    "and the job's terminology ONLY where it is truthful given the input. "
    "Hard rules: never invent employers, job titles, dates, numbers/metrics, or "
    "technologies that are not already present; keep exactly the same number of "
    "bullets; keep each to at most two lines. "
    'Return strict JSON of the form {"bullets": ["...", "..."]}.'
)

# Backward-compat alias: existing callers (coverletter, resume_import, tests)
# import OllamaClient from this module.  They all use available()/has_model()/
# chat()/chat_json() — all present on OllamaBackend.
OllamaClient = OllamaBackend


class LLMTailor:
    """Tailor that rephrases bullets with an LLM backend, atop the keyword tailor."""

    def __init__(self, client: ChatBackend, base: Tailor | None = None) -> None:
        self._client = client
        self._base: Tailor = base or KeywordTailor()

    def tailor(self, profile: Profile, job_description: str) -> TailorResult:
        # Always start from the deterministic result (reorder + a clean deep copy).
        result = self._base.tailor(profile, job_description)
        if not job_description or not self._client.available() or not self._client.ready():
            logger.info("LLM tailor unavailable — using deterministic result")
            return result

        tailored = result.profile  # already a deep copy owned by us
        for xp in tailored.experience:
            if xp.bullets:
                xp.bullets = self._rephrase(
                    xp.bullets, job_description, f"{xp.role} at {xp.company}"
                )
        for pr in tailored.projects:
            if pr.bullets:
                pr.bullets = self._rephrase(pr.bullets, job_description, pr.name)

        # Recompute coverage against the rephrased text.
        rescored = self._base.tailor(tailored, job_description)
        return TailorResult(
            profile=tailored,
            score=rescored.score,
            matched_keywords=rescored.matched_keywords,
            missing_keywords=rescored.missing_keywords,
        )

    def _rephrase(self, bullets: list[str], job_description: str, context: str) -> list[str]:
        user = json.dumps({"job": job_description[:2000], "context": context, "bullets": bullets})
        try:
            data = self._client.chat_json(_SYSTEM_PROMPT, user)
            new = data.get("bullets")
            if (
                isinstance(new, list)
                and len(new) == len(bullets)
                and all(isinstance(b, str) and b.strip() for b in new)
            ):
                return [b.strip() for b in new]
            logger.warning("LLM returned malformed/mismatched bullets — keeping originals")
        except Exception as exc:
            logger.warning("LLM rephrase failed ({}); keeping originals", exc)
        return bullets


# Convenience: build an LLMTailor from current settings if the backend is ready.


def build_llm_tailor_if_ready() -> LLMTailor | None:
    """Return a ready LLMTailor from current settings, or None if unavailable."""
    from job_sentinel.config.settings import LLMSettings
    from job_sentinel.documents.providers import build_chat_backend

    llm_settings = LLMSettings()
    backend = build_chat_backend(llm_settings)
    if backend.available() and backend.ready():
        return LLMTailor(backend)
    return None


def _chat_json_compat(client: Any, system: str, user: str) -> dict[str, Any]:
    """Call chat_json on anything that has that method (duck-typed for compat)."""
    result: dict[str, Any] = client.chat_json(system, user)
    return result
