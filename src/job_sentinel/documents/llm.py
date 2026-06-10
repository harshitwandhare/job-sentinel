"""
documents/llm.py
─────────────────
Optional local-LLM tailoring layer.

This is the "harder but truly open" path: instead of a hosted API, we talk to a
**local** model served by Ollama (https://ollama.com) over its HTTP API. The
:class:`LLMTailor` implements the same :class:`~job_sentinel.documents.tailor.Tailor`
Protocol as the deterministic tailor, so callers don't change.

Design guarantees
─────────────────
- **Always degrades gracefully.** If Ollama isn't installed/reachable or the
  model isn't pulled, we fall back to the deterministic keyword tailor — the
  product never *requires* the heavy piece.
- **No fabrication.** The model is only allowed to *rephrase* bullets that are
  already in the profile; the prompt forbids inventing employers, titles, dates,
  metrics, or technologies. Output is JSON-validated and length-checked; any
  deviation means we keep the original bullets.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
from loguru import logger

from job_sentinel.documents.tailor import KeywordTailor, TailorResult

if TYPE_CHECKING:
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


class OllamaClient:
    """Thin client for a local Ollama server's HTTP API."""

    def __init__(self, base_url: str, model: str, timeout: float = 90.0) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        """True if the Ollama server answers."""
        try:
            httpx.get(f"{self._base}/api/tags", timeout=3.0).raise_for_status()
        except Exception:
            return False
        return True

    def installed_models(self) -> list[str]:
        """Names of locally-pulled models (empty if the server is unreachable)."""
        try:
            resp = httpx.get(f"{self._base}/api/tags", timeout=3.0)
            resp.raise_for_status()
            return [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:
            return []

    def has_model(self) -> bool:
        """True if the configured model (or its base tag) is pulled."""
        base = self._model.split(":")[0]
        return any(
            name == self._model or name.split(":")[0] == base for name in self.installed_models()
        )

    def chat(self, system: str, messages: list[dict[str, str]]) -> str:
        """
        Plain-text multi-turn chat (no JSON forcing) — used by the assistant.

        ``messages`` are prior turns as ``{"role", "content"}`` dicts; the system
        prompt is prepended. Thinking stays disabled so reasoning models answer
        directly.
        """
        payload = {
            "model": self._model,
            "stream": False,
            "think": False,
            "messages": [{"role": "system", "content": system}, *messages],
            "options": {"temperature": 0.4},
        }
        resp = httpx.post(f"{self._base}/api/chat", json=payload, timeout=self._timeout)
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")
        return str(content).strip()

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        """Single non-streaming chat turn constrained to JSON output."""
        payload = {
            "model": self._model,
            "stream": False,
            "format": "json",
            # Disable chain-of-thought for "thinking" models (Qwen3, etc.):
            # bullet rephrasing doesn't need reasoning traces, and leaving it on
            # makes a 30B-class model spend minutes per call. Ignored by models
            # that don't support it.
            "think": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": 0.2},
        }
        resp = httpx.post(f"{self._base}/api/chat", json=payload, timeout=self._timeout)
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "{}")
        parsed: dict[str, Any] = json.loads(content)
        return parsed


class LLMTailor:
    """Tailor that rephrases bullets with a local LLM, atop the keyword tailor."""

    def __init__(self, client: OllamaClient, base: Tailor | None = None) -> None:
        self._client = client
        self._base: Tailor = base or KeywordTailor()

    def tailor(self, profile: Profile, job_description: str) -> TailorResult:
        # Always start from the deterministic result (reorder + a clean deep copy).
        result = self._base.tailor(profile, job_description)
        if not job_description or not self._client.available() or not self._client.has_model():
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
