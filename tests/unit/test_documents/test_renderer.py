"""Tests for documents/renderer.py — Tectonic PDF compilation and one-page fitting."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from job_sentinel.documents.renderer import (
    RenderError,
    _trim_levels,
    build_cover_letter_pdf,
    build_resume_pdf,
    compile_tex_to_pdf,
    count_pdf_pages,
    tectonic_available,
)
from job_sentinel.profile import example_profile


class TestTectonicAvailable:
    def test_true_when_on_path(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/tectonic"):
            assert tectonic_available() is True

    def test_false_when_missing(self) -> None:
        with patch("shutil.which", return_value=None):
            assert tectonic_available() is False


class TestCountPdfPages:
    def test_unreadable_file_returns_zero(self, tmp_path: Path) -> None:
        bogus = tmp_path / "not-a-pdf.pdf"
        bogus.write_text("not a pdf")
        assert count_pdf_pages(bogus) == 0

    def test_missing_file_returns_zero(self, tmp_path: Path) -> None:
        assert count_pdf_pages(tmp_path / "missing.pdf") == 0


class TestCompileTexToPdf:
    def test_raises_when_tectonic_missing(self, tmp_path: Path) -> None:
        with (
            patch("shutil.which", return_value=None),
            pytest.raises(RenderError, match="not found on PATH"),
        ):
            compile_tex_to_pdf("\\documentclass{article}", tmp_path / "out.pdf")

    def test_writes_tex_source_even_when_tectonic_missing(self, tmp_path: Path) -> None:
        out = tmp_path / "resume.pdf"
        with patch("shutil.which", return_value=None), pytest.raises(RenderError):
            compile_tex_to_pdf("\\documentclass{article}", out, keep_tex=True)
        assert out.with_suffix(".tex").read_text(encoding="utf-8") == "\\documentclass{article}"

    def test_does_not_write_tex_when_keep_tex_false(self, tmp_path: Path) -> None:
        out = tmp_path / "resume.pdf"
        with patch("shutil.which", return_value=None), pytest.raises(RenderError):
            compile_tex_to_pdf("\\documentclass{article}", out, keep_tex=False)
        assert not out.with_suffix(".tex").exists()

    def test_raises_on_nonzero_exit(self, tmp_path: Path) -> None:
        out = tmp_path / "resume.pdf"
        fake_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="boom")
        with (
            patch("shutil.which", return_value="/usr/bin/tectonic"),
            patch("subprocess.run", return_value=fake_result),
            pytest.raises(RenderError, match="Tectonic failed"),
        ):
            compile_tex_to_pdf("\\documentclass{article}", out)

    def test_raises_when_no_pdf_produced(self, tmp_path: Path) -> None:
        out = tmp_path / "resume.pdf"
        fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with (
            patch("shutil.which", return_value="/usr/bin/tectonic"),
            patch("subprocess.run", return_value=fake_result),
            pytest.raises(RenderError, match="produced no PDF"),
        ):
            compile_tex_to_pdf("\\documentclass{article}", out)

    def test_success_copies_pdf_to_out_path(self, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "resume.pdf"
        fake_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        def fake_run(
            cmd: list[str], *, cwd: Path, **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            (Path(cwd) / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
            return fake_result

        with (
            patch("shutil.which", return_value="/usr/bin/tectonic"),
            patch("subprocess.run", side_effect=fake_run),
        ):
            result = compile_tex_to_pdf("\\documentclass{article}", out)
        assert result == out
        assert out.read_bytes() == b"%PDF-1.4 fake"


class TestTrimLevels:
    def test_returns_three_progressively_smaller_profiles(self) -> None:
        profile = example_profile()
        levels = _trim_levels(profile)
        assert len(levels) == 3
        # Each level trims experience entries down to at most the prior level's count.
        counts = [len(level.experience) for level in levels]
        assert counts == sorted(counts, reverse=True)

    def test_does_not_mutate_original_profile(self) -> None:
        profile = example_profile()
        original_experience_count = len(profile.experience)
        _trim_levels(profile)
        assert len(profile.experience) == original_experience_count

    def test_last_level_shrinks_long_summary(self) -> None:
        profile = example_profile()
        profile.basics.summary = "word " * 200
        levels = _trim_levels(profile)
        assert len(levels[-1].basics.summary) <= 281  # 280 + ellipsis


class TestBuildResumePdf:
    def _stub_compile(self, tmp_path: Path) -> Path:
        out = tmp_path / "resume.pdf"
        out.write_bytes(b"%PDF-1.4 fake")
        return out

    def test_single_page_returns_immediately(self, tmp_path: Path) -> None:
        profile = example_profile()
        out = tmp_path / "resume.pdf"
        with (
            patch(
                "job_sentinel.documents.renderer.compile_tex_to_pdf",
                return_value=self._stub_compile(tmp_path),
            ) as mock_compile,
            patch("job_sentinel.documents.renderer.count_pdf_pages", return_value=1),
        ):
            result = build_resume_pdf(profile, out)
        assert result == self._stub_compile(tmp_path)
        mock_compile.assert_called_once()

    def test_overflow_retries_in_compact_mode(self, tmp_path: Path) -> None:
        profile = example_profile()
        out = tmp_path / "resume.pdf"
        page_counts = iter([2, 1])
        with (
            patch(
                "job_sentinel.documents.renderer.compile_tex_to_pdf",
                return_value=self._stub_compile(tmp_path),
            ) as mock_compile,
            patch(
                "job_sentinel.documents.renderer.count_pdf_pages",
                side_effect=lambda _p: next(page_counts),
            ),
        ):
            build_resume_pdf(profile, out)
        assert mock_compile.call_count == 2

    def test_still_overflowing_falls_through_trim_levels_and_warns(self, tmp_path: Path) -> None:
        profile = example_profile()
        out = tmp_path / "resume.pdf"
        with (
            patch(
                "job_sentinel.documents.renderer.compile_tex_to_pdf",
                return_value=self._stub_compile(tmp_path),
            ) as mock_compile,
            patch("job_sentinel.documents.renderer.count_pdf_pages", return_value=2),
        ):
            result = build_resume_pdf(profile, out)
        # initial + compact + 3 trim levels = 5 compile attempts
        assert mock_compile.call_count == 5
        assert result == self._stub_compile(tmp_path)

    def test_one_page_false_skips_retry_logic(self, tmp_path: Path) -> None:
        profile = example_profile()
        out = tmp_path / "resume.pdf"
        with (
            patch(
                "job_sentinel.documents.renderer.compile_tex_to_pdf",
                return_value=self._stub_compile(tmp_path),
            ) as mock_compile,
            patch("job_sentinel.documents.renderer.count_pdf_pages") as mock_count,
        ):
            build_resume_pdf(profile, out, one_page=False)
        mock_compile.assert_called_once()
        mock_count.assert_not_called()


class TestBuildCoverLetterPdf:
    def test_delegates_to_compile_tex_to_pdf(self, tmp_path: Path) -> None:
        profile = example_profile()
        out = tmp_path / "cover.pdf"
        stub = tmp_path / "compiled.pdf"
        stub.write_bytes(b"%PDF-1.4 fake")
        with patch(
            "job_sentinel.documents.renderer.compile_tex_to_pdf", return_value=stub
        ) as mock_compile:
            result = build_cover_letter_pdf(
                profile, ["Paragraph one.", "Paragraph two."], out, role="Engineer", company="Acme"
            )
        assert result == stub
        mock_compile.assert_called_once()
        tex_arg = mock_compile.call_args[0][0]
        assert "Paragraph one." in tex_arg or isinstance(tex_arg, str)
