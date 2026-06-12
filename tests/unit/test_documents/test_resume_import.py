"""
Tests for resume PDF import: text extraction guards, the heuristic parser,
and the LLM-first path with a fake client.
"""

from __future__ import annotations

import pytest

from job_sentinel.documents.resume_import import (
    ResumeImportError,
    extract_pdf_text,
    parse_resume_text,
)

SAMPLE_RESUME = """\
Harshit Wandhare
Dallas, TX | +91 9307633967 | dal314006@utdallas.edu | linkedin.com/in/harshit-wandhare

Summary
Graduate student at UT Dallas with 2.5+ years of professional experience.

Experience
Yosemite Crew (DuneXploration UG, Germany) Sep 2025 -- Jul 2026
Product Engineer (Full-Time, Remote)
• Served as a core team member on an open-source healthcare platform.
• Communicated complex information clearly to non-technical stakeholders.

Reliance Jio Platforms Limited, Mumbai, India Oct 2023 -- Sep 2025
Software Development Engineer I
• Supported enterprise applications serving 100,000+ monthly users.

Education
University of Texas at Dallas Aug 2026 -- May 2028
Master of Science in Computer Science

Vidyalankar Institute of Technology 2019 -- 2023
Bachelor of Engineering in Computer Science (CGPA: 9.53 / 10.0)

Skills
Languages: Python, TypeScript, SQL
Tools: Docker, Git, Playwright
"""


# ── extract_pdf_text ──────────────────────────────────────────────────────────


def test_extract_rejects_garbage_bytes() -> None:
    with pytest.raises(ResumeImportError, match="Could not read"):
        extract_pdf_text(b"this is not a pdf")


def test_extract_rejects_textless_pdf() -> None:
    import io

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)

    with pytest.raises(ResumeImportError, match="scanned image"):
        extract_pdf_text(buf.getvalue())


# ── heuristic parser ─────────────────────────────────────────────────────────


def test_heuristic_extracts_basics() -> None:
    profile = parse_resume_text(SAMPLE_RESUME)
    assert profile.basics.name == "Harshit Wandhare"
    assert profile.basics.email == "dal314006@utdallas.edu"
    assert "9307633967" in profile.basics.phone
    assert any("linkedin.com" in link.url for link in profile.basics.links)
    assert profile.basics.links[0].url.startswith("https://")
    assert "Graduate student" in profile.basics.summary


def test_heuristic_extracts_experience_with_bullets() -> None:
    profile = parse_resume_text(SAMPLE_RESUME)
    assert len(profile.experience) == 2
    first = profile.experience[0]
    assert "Yosemite Crew" in first.company
    assert first.start == "Sep 2025"
    assert first.end == "Jul 2026"
    assert first.role.startswith("Product Engineer")
    assert len(first.bullets) == 2
    assert first.bullets[0].startswith("Served as a core team member")


def test_heuristic_extracts_education_and_gpa() -> None:
    profile = parse_resume_text(SAMPLE_RESUME)
    assert len(profile.education) == 2
    assert "University of Texas at Dallas" in profile.education[0].institution
    assert profile.education[1].gpa.startswith("9.53")


def test_heuristic_extracts_skill_groups() -> None:
    profile = parse_resume_text(SAMPLE_RESUME)
    categories = {g.category: g.skills for g in profile.skills}
    assert categories["Languages"] == ["Python", "TypeScript", "SQL"]
    assert "Docker" in categories["Tools"]


def test_empty_sections_yield_empty_profile_lists() -> None:
    profile = parse_resume_text("Just A Name\nnothing else here")
    assert profile.basics.name == "Just A Name"
    assert profile.experience == []
    assert profile.education == []


# ── LLM-first path ───────────────────────────────────────────────────────────


class _FakeClient:
    """Stands in for OllamaClient.chat_json."""

    def __init__(self, payload: dict | Exception) -> None:
        self._payload = payload

    def chat_json(self, system: str, user: str) -> dict:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_llm_result_is_validated_and_used() -> None:
    payload = {
        "basics": {"name": "LLM Name", "email": "x@y.z"},
        "experience": [{"company": "Acme", "role": "Engineer", "bullets": ["did things"]}],
    }
    profile = parse_resume_text(SAMPLE_RESUME, client=_FakeClient(payload))
    assert profile.basics.name == "LLM Name"
    assert profile.experience[0].company == "Acme"


def test_llm_failure_falls_back_to_heuristic() -> None:
    profile = parse_resume_text(SAMPLE_RESUME, client=_FakeClient(RuntimeError("model down")))
    assert profile.basics.name == "Harshit Wandhare"  # heuristic result


def test_llm_empty_reply_falls_back_to_heuristic() -> None:
    profile = parse_resume_text(SAMPLE_RESUME, client=_FakeClient({}))
    assert profile.basics.name == "Harshit Wandhare"
