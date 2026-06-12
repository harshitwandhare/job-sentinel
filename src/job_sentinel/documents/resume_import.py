"""
documents/resume_import.py
───────────────────────────
Turn an uploaded resume PDF into a :class:`Profile` draft.

Pipeline
────────
1. ``extract_pdf_text`` — pull the text layer out of the PDF (pypdf). Scanned
   image-only resumes have no text layer; we report that clearly rather than
   returning an empty profile.
2. ``parse_resume_text`` — try the local LLM first (it reads layout-mangled
   text far better than rules); validate its JSON against the Profile schema.
   If the model is unavailable or returns junk, fall back to a deterministic
   heuristic parser (regex contact extraction + section splitting).

The result is a **draft**: callers (API/UI/CLI) show it to the user for review
before saving — extraction is never silently authoritative.
"""

from __future__ import annotations

import io
import re
from typing import TYPE_CHECKING

from loguru import logger

from job_sentinel.profile.models import (
    Basics,
    Education,
    Experience,
    Link,
    Profile,
    Project,
    SkillGroup,
)

if TYPE_CHECKING:
    from job_sentinel.documents.llm import OllamaClient


class ResumeImportError(ValueError):
    """The PDF couldn't be read or contains no extractable text."""


# ─────────────────────────────────────────────────────────────────────────────
# 1) PDF → text
# ─────────────────────────────────────────────────────────────────────────────


def extract_pdf_text(data: bytes) -> str:
    """Extract the text layer from PDF bytes. Raises ResumeImportError if empty."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency declared in pyproject
        msg = "pypdf is not installed — run: pip install pypdf"
        raise ResumeImportError(msg) from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        msg = f"Could not read the PDF: {exc}"
        raise ResumeImportError(msg) from exc

    text = "\n".join(pages).strip()
    if not text:
        msg = (
            "No text found in the PDF — it looks like a scanned image. "
            "Export the resume as a text-based PDF and try again."
        )
        raise ResumeImportError(msg)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# 2) text → Profile
# ─────────────────────────────────────────────────────────────────────────────

_LLM_PROMPT = """\
Extract a structured profile from this resume text. Reply with ONLY a JSON \
object (no markdown fences, no commentary) with exactly these keys:

{{"basics": {{"name": "", "headline": "", "email": "", "phone": "", "location": "",
  "links": [{{"label": "", "url": ""}}], "summary": ""}},
 "education": [{{"institution": "", "degree": "", "location": "", "start": "", "end": "",
  "gpa": "", "highlights": []}}],
 "experience": [{{"company": "", "role": "", "location": "", "start": "", "end": "",
  "bullets": []}}],
 "projects": [{{"name": "", "description": "", "url": "", "bullets": []}}],
 "skills": [{{"category": "", "skills": []}}],
 "certifications": [{{"name": "", "issuer": "", "date": ""}}],
 "awards": [{{"title": "", "issuer": "", "date": "", "description": ""}}],
 "publications": [{{"title": "", "venue": "", "date": "", "url": ""}}]}}

Keep dates as written (e.g. "Oct 2023 -- Sep 2025"). Use empty strings/lists \
for anything absent. Resume text:

{text}
"""


def parse_resume_text(text: str, client: OllamaClient | None = None) -> Profile:
    """Parse resume text into a Profile, preferring the local LLM when given."""
    if client is not None:
        profile = _parse_with_llm(text, client)
        if profile is not None:
            return profile
        logger.info("LLM extraction failed or unavailable — using heuristic parser")
    return _parse_heuristic(text)


def _parse_with_llm(text: str, client: OllamaClient) -> Profile | None:
    try:
        data = client.chat_json(
            "You extract structured data from resumes. Reply with only JSON.",
            _LLM_PROMPT.format(text=text[:12_000]),
        )
        if not data:
            return None
        return Profile.model_validate(data)
    except Exception as exc:
        logger.debug("LLM resume extraction failed: {}", exc)
        return None


# ── Heuristic fallback ────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}")
_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?((?:linkedin\.com|github\.com|gitlab\.com)/\S+)")
_DATE_RANGE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})"
    r"\s*(?:[-–—]+|to)\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|[Pp]resent)",
)
_GPA_RE = re.compile(r"(?:GPA|CGPA)[:\s]*([\d.]+(?:\s*/\s*[\d.]+)?)", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[•·▪‣◦*–-]\s+")

_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "objective", "about", "professional summary"),
    "education": ("education", "academics"),
    "experience": (
        "experience",
        "work experience",
        "employment",
        "professional experience",
        "additional experience",
        "additional experience & activities",
    ),
    "projects": ("projects", "personal projects", "academic projects"),
    "skills": ("skills", "technical skills", "relevant skills"),
    "certifications": ("certifications", "certificates", "licenses"),
    "awards": ("awards", "honors", "achievements"),
    "publications": ("publications", "research"),
}


def _section_of(line: str) -> str | None:
    """Return the canonical section key if this line is a section header."""
    candidate = line.strip().rstrip(":").lower()
    if not candidate or len(candidate) > 45:
        return None
    for key, aliases in _SECTION_ALIASES.items():
        if candidate in aliases:
            return key
    return None


def _parse_heuristic(text: str) -> Profile:
    """Deterministic best-effort parser. Imperfect by design — output is a draft."""
    lines = [ln.rstrip() for ln in text.splitlines()]

    basics = _extract_basics(lines)
    sections = _split_sections(lines)

    profile = Profile(basics=basics)
    if "summary" in sections:
        profile.basics.summary = " ".join(ln.strip() for ln in sections["summary"] if ln.strip())[
            :1200
        ]
    if "education" in sections:
        profile.education = _parse_education(sections["education"])
    if "experience" in sections:
        profile.experience = _parse_experience(sections["experience"])
    if "projects" in sections:
        profile.projects = _parse_projects(sections["projects"])
    if "skills" in sections:
        profile.skills = _parse_skills(sections["skills"])
    return profile


def _extract_basics(lines: list[str]) -> Basics:
    head = "\n".join(lines[:15])
    email = m.group(0) if (m := _EMAIL_RE.search(head)) else ""
    phone = m.group(0) if (m := _PHONE_RE.search(head)) else ""
    links = [
        Link(label=_link_label(u), url=f"https://{u.rstrip('|,;')}") for u in _URL_RE.findall(head)
    ]

    name = ""
    for ln in lines[:6]:
        candidate = ln.strip()
        if (
            candidate
            and "@" not in candidate
            and not any(ch.isdigit() for ch in candidate)
            and 1 <= len(candidate.split()) <= 5
            and _section_of(candidate) is None
        ):
            name = candidate
            break

    location = ""
    # "City, ST |" patterns in the contact line
    loc_match = re.search(r"([A-Z][a-zA-Z .]+,\s*[A-Z]{2})\b", head)
    if loc_match:
        location = loc_match.group(1)

    return Basics(name=name, email=email, phone=phone, location=location, links=links)


def _link_label(url: str) -> str:
    if "linkedin" in url:
        return "LinkedIn"
    if "github" in url:
        return "GitHub"
    return "Link"


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for ln in lines:
        key = _section_of(ln)
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(ln)
    return sections


def _split_entries(lines: list[str]) -> list[list[str]]:
    """Group section lines into entries: a new entry starts at a date-range line."""
    entries: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            continue
        is_new_entry = bool(_DATE_RANGE_RE.search(stripped)) and not _BULLET_RE.match(ln)
        if is_new_entry and current:
            entries.append(current)
            current = []
        current.append(ln)
    if current:
        entries.append(current)
    return entries


def _parse_experience(lines: list[str]) -> list[Experience]:
    out = []
    for entry in _split_entries(lines):
        header = entry[0].strip()
        dates = _DATE_RANGE_RE.search(header)
        start, end = (dates.group(1), dates.group(2)) if dates else ("", "")
        company = _DATE_RANGE_RE.sub("", header).strip(" |·—–-")
        role = ""
        rest = entry[1:]
        if rest and not _BULLET_RE.match(rest[0]):
            role = rest[0].strip(" |·")
            rest = rest[1:]
        bullets = [_BULLET_RE.sub("", ln).strip() for ln in rest if ln.strip()]
        out.append(Experience(company=company, role=role, start=start, end=end, bullets=bullets))
    return out


def _parse_education(lines: list[str]) -> list[Education]:
    out = []
    for entry in _split_entries(lines):
        block = " ".join(entry)
        dates = _DATE_RANGE_RE.search(block)
        start, end = (dates.group(1), dates.group(2)) if dates else ("", "")
        gpa = m.group(1) if (m := _GPA_RE.search(block)) else ""
        institution = _DATE_RANGE_RE.sub("", entry[0]).strip(" |·—–-")
        degree = entry[1].strip(" |·") if len(entry) > 1 else ""
        degree = _GPA_RE.sub("", degree).strip(" ()—–-")
        out.append(Education(institution=institution, degree=degree, start=start, end=end, gpa=gpa))
    return out


def _parse_projects(lines: list[str]) -> list[Project]:
    out = []
    for entry in _split_entries(lines) or ([lines] if any(ln.strip() for ln in lines) else []):
        name = entry[0].strip(" |·—–-")
        bullets = [_BULLET_RE.sub("", ln).strip() for ln in entry[1:] if ln.strip()]
        out.append(Project(name=name[:120], bullets=bullets))
    return out


def _parse_skills(lines: list[str]) -> list[SkillGroup]:
    groups = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            continue
        if ":" in stripped:
            category, _, rest = stripped.partition(":")
            skills = [s.strip() for s in re.split(r"[,;]", rest) if s.strip()]
            if skills:
                groups.append(SkillGroup(category=category.strip(), skills=skills))
        elif "," in stripped:
            skills = [s.strip() for s in stripped.split(",") if s.strip()]
            groups.append(SkillGroup(category="Skills", skills=skills))
    return groups
