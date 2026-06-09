"""Tests for LaTeX escaping and resume template rendering."""

from __future__ import annotations

from job_sentinel.documents import latex_escape, render_resume_tex
from job_sentinel.profile import Basics, Experience, Profile, SkillGroup, example_profile


class TestLatexEscape:
    def test_ampersand_and_percent(self) -> None:
        assert latex_escape("R&D 50% off") == r"R\&D 50\% off"

    def test_underscore_and_hash(self) -> None:
        assert latex_escape("a_b #1") == r"a\_b \#1"

    def test_backslash(self) -> None:
        assert latex_escape("a\\b") == r"a\textbackslash{}b"

    def test_none_is_empty(self) -> None:
        assert latex_escape(None) == ""


class TestRenderResumeTex:
    def test_example_renders_complete_document(self) -> None:
        tex = render_resume_tex(example_profile())
        assert tex.lstrip().startswith("\\documentclass")
        assert "\\begin{document}" in tex
        assert "\\end{document}" in tex

    def test_includes_header_and_sections(self) -> None:
        tex = render_resume_tex(example_profile())
        assert "Your Name" in tex
        assert "\\section{Experience}" in tex
        assert "\\section{Skills}" in tex

    def test_special_chars_in_content_are_escaped(self) -> None:
        p = Profile(
            basics=Basics(name="Jane & John"),
            experience=[Experience(company="A_B Corp", role="R&D Lead", bullets=["Cut cost 30%"])],
            skills=[SkillGroup(category="Langs", skills=["C#", "F#"])],
        )
        tex = render_resume_tex(p)
        assert r"Jane \& John" in tex
        assert r"A\_B Corp" in tex
        assert r"R\&D Lead" in tex
        assert r"Cut cost 30\%" in tex

    def test_empty_optional_sections_are_omitted(self) -> None:
        tex = render_resume_tex(Profile(basics=Basics(name="Solo")))
        assert "\\section{Experience}" not in tex
        assert "\\section{Publications}" not in tex
        assert "Solo" in tex
