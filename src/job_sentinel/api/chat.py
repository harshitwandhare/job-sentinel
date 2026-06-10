"""
api/chat.py
────────────
The Sentinel assistant: a chat interface over the app's own data.

Design rule: **tools for facts, LLM for language.** Questions about the user's
jobs, deadlines, stats, or profile are answered deterministically from SQLite /
profile.yaml — the model is never asked to recall facts it could hallucinate.
The local LLM (when available) handles everything else, grounded with a compact
context block built from the same data. With no model installed, the assistant
still answers every data question and explains its capabilities — the chat is
useful, not a brick.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from loguru import logger
from pydantic import BaseModel, Field

from job_sentinel.core.deadlines import days_until
from job_sentinel.core.models import ApplicationStatus
from job_sentinel.documents.tailor import KeywordTailor
from job_sentinel.profile import load_profile

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from job_sentinel.core.models import JobPosting
    from job_sentinel.documents.llm import OllamaClient
    from job_sentinel.profile.models import Profile

_MAX_CONTEXT_JOBS = 6
_JD_LENGTH_HINT = 400  # a message this long is almost certainly a pasted job description

_SYSTEM_PROMPT = (
    "You are Sentinel, the built-in assistant of Job Sentinel — a local-first, open-source "
    "job-hunt platform (job monitoring, deadline tracking, ATS résumé and cover-letter "
    "generation with a local LLM). Answer questions about the job hunt, résumés, and using "
    "the app. For facts about the user's own jobs and profile, rely ONLY on the CONTEXT "
    "block; if something isn't in it, say you don't have it and name the feature that does "
    "(e.g. the Jobs page or `job-sentinel scrape`). Be concise and concrete. Never invent "
    "postings, dates, or profile facts."
)

_HELP = (
    "I can help with:\n"
    '• **Deadlines** — "what\'s closing soon?"\n'
    '• **Tracked jobs** — "show my recent jobs"\n'
    '• **Pipeline stats** — "how many have I applied to?"\n'
    '• **Your profile** — "summarize my profile"\n'
    "• **ATS match** — paste a full job description and I'll score your profile against it\n"
    "• Anything else about the job hunt or this app — answered by your local model when "
    "Ollama is running (`job-sentinel resume doctor` to check)."
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatReply(BaseModel):
    reply: str
    source: Literal["rules", "llm"]


# ── Deterministic answers (the "tools") ───────────────────────────────────────


def _open_jobs(db_path: Path) -> list[JobPosting]:
    from job_sentinel.db.repository import JobRepository

    if not db_path.is_file():
        return []
    repo = JobRepository(db_path)
    try:
        return repo.get_by_status(ApplicationStatus.NEW) + repo.get_by_status(
            ApplicationStatus.SEEN
        )
    finally:
        repo.close()


def _recent_jobs(db_path: Path, limit: int = _MAX_CONTEXT_JOBS) -> list[JobPosting]:
    from job_sentinel.db.repository import JobRepository

    if not db_path.is_file():
        return []
    repo = JobRepository(db_path)
    try:
        return repo.get_recent_jobs(limit=limit)
    finally:
        repo.close()


def _stats(db_path: Path) -> dict[str, int]:
    from job_sentinel.db.repository import JobRepository

    if not db_path.is_file():
        return {}
    repo = JobRepository(db_path)
    try:
        return repo.get_stats()
    finally:
        repo.close()


def _answer_deadlines(db_path: Path) -> str:
    soon: list[tuple[int, JobPosting]] = []
    for job in _open_jobs(db_path):
        n = days_until(job.deadline)
        if n is not None and 0 <= n <= 14:
            soon.append((n, job))
    if not soon:
        return (
            "Nothing I'm tracking closes in the next 14 days. "
            "If you haven't scraped recently, run `job-sentinel scrape` to refresh."
        )
    soon.sort(key=lambda t: t[0])
    lines = ["Closing soon:"]
    for n, job in soon[:8]:
        when = "today" if n == 0 else ("tomorrow" if n == 1 else f"in {n} days")
        lines.append(f"• **{job.title}** ({job.employer or 'unknown'}) — {when}")
    return "\n".join(lines)


def _answer_recent(db_path: Path) -> str:
    jobs = _recent_jobs(db_path)
    if not jobs:
        return (
            "No jobs tracked yet. Run `job-sentinel login` once, then "
            "`job-sentinel scrape` — postings will appear here and on the Jobs page."
        )
    lines = ["Most recently tracked:"]
    for j in jobs:
        bits = " · ".join(b for b in (j.employer, j.status.value) if b)
        lines.append(f"• **{j.title}** ({bits})")
    return "\n".join(lines)


def _answer_stats(db_path: Path) -> str:
    counts = _stats(db_path)
    if not counts.get("total"):
        return "The pipeline is empty so far — run a scrape and check back."
    return (
        f"Pipeline: **{counts.get('total', 0)}** tracked — "
        f"{counts.get('new', 0)} new, {counts.get('seen', 0)} seen, "
        f"{counts.get('applied', 0)} applied, {counts.get('ignored', 0)} ignored, "
        f"{counts.get('closed', 0)} closed."
    )


def _answer_profile(profile: Profile) -> str:
    if profile.is_empty():
        return (
            "Your profile is empty. Build it on the Edit page or with "
            "`job-sentinel resume init` — everything else (tailoring, PDFs, this chat) "
            "gets smarter once it exists."
        )
    top_skills = ", ".join(profile.skills[0].skills[:6]) if profile.skills else "—"
    latest = profile.experience[0] if profile.experience else None
    role_line = f"{latest.role} at {latest.company}" if latest else "no experience entries yet"
    return (
        f"**{profile.basics.name}** — {profile.basics.headline or 'no headline set'}.\n"
        f"Latest role: {role_line}. "
        f"{len(profile.experience)} experience entries, {len(profile.projects)} projects, "
        f"{len(profile.education)} education entries.\nTop skills: {top_skills}."
    )


def _answer_jd_match(profile: Profile, jd: str) -> str:
    if profile.is_empty():
        return "I can score a job description once your profile exists — build it first."
    result = KeywordTailor().tailor(profile, jd)
    missing = ", ".join(result.missing_keywords[:10]) or "nothing significant"
    return (
        f"ATS keyword coverage for that posting: **{result.score_pct}%**.\n"
        f"Missing terms worth weaving in: {missing}.\n"
        f"Generate the tailored PDF from the Studio page, or "
        f'`job-sentinel resume build --ai --semantic --job-text "…"`.'
    )


# ── Context for the LLM ───────────────────────────────────────────────────────


def _context_block(profile: Profile, db_path: Path) -> str:
    parts: list[str] = []
    if not profile.is_empty():
        parts.append(_answer_profile(profile))
    stats_line = _answer_stats(db_path)
    parts.append(stats_line)
    jobs = _recent_jobs(db_path)
    if jobs:
        parts.append("Recent jobs: " + "; ".join(f"{j.title} [{j.status.value}]" for j in jobs))
    return "\n".join(parts)[:3000]


# ── Router ────────────────────────────────────────────────────────────────────


def answer(
    messages: list[ChatMessage],
    *,
    profile_path: Path,
    db_path: Path,
    client_factory: Callable[[], OllamaClient | None] | None = None,
) -> ChatReply:
    """
    Answer the latest user message. Deterministic for data; LLM for the rest.

    ``client_factory`` is called only when the LLM branch is actually reached,
    so rules-routed questions never pay the model-availability probe.
    """
    question = messages[-1].content.strip()
    q = question.lower()
    profile = load_profile(profile_path)

    if any(k in q for k in ("help", "what can you do", "how do you work", "commands")):
        return ChatReply(reply=_HELP, source="rules")
    if len(question) >= _JD_LENGTH_HINT:
        return ChatReply(reply=_answer_jd_match(profile, question), source="rules")
    if any(k in q for k in ("deadline", "closing", "due soon", "closes")):
        return ChatReply(reply=_answer_deadlines(db_path), source="rules")
    if any(k in q for k in ("recent job", "latest job", "my jobs", "tracked job", "postings")):
        return ChatReply(reply=_answer_recent(db_path), source="rules")
    if any(k in q for k in ("stats", "pipeline", "how many", "applied to")):
        return ChatReply(reply=_answer_stats(db_path), source="rules")
    if any(k in q for k in ("profile", "about me", "my experience", "my skills", "who am i")):
        return ChatReply(reply=_answer_profile(profile), source="rules")

    client = client_factory() if client_factory is not None else None
    if client is not None:
        try:
            context = _context_block(profile, db_path)
            turns = [{"role": m.role, "content": m.content} for m in messages[-10:]]
            system = f"{_SYSTEM_PROMPT}\n\nCONTEXT:\n{context}"
            reply = client.chat(system, turns)
            if reply:
                return ChatReply(reply=reply, source="llm")
        except Exception as exc:
            logger.warning("Assistant LLM call failed ({}); falling back to rules", exc)

    return ChatReply(
        reply=(
            "I couldn't reach the local model for that one — start Ollama and check with "
            "`job-sentinel resume doctor`. Meanwhile, here's what I can always do:\n\n" + _HELP
        ),
        source="rules",
    )
