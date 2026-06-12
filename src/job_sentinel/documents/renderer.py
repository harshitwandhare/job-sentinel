"""
documents/renderer.py
──────────────────────
Compile the rendered LaTeX into a PDF using **Tectonic**.

Tectonic is a self-contained LaTeX engine (single binary, downloads the
packages it needs on first use and caches them) — so a user only installs one
thing and gets reproducible output, no full TeX Live install required.

If Tectonic isn't on the PATH we raise :class:`RenderError` with an install
hint rather than a cryptic ``FileNotFoundError``, and we still write the
``.tex`` so the user can compile it elsewhere (e.g. Overleaf).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from job_sentinel.documents.latex import render_resume_tex, render_template

if TYPE_CHECKING:
    from job_sentinel.profile.models import Profile

_INSTALL_HINT = (
    "Tectonic was not found on PATH. Install it (https://tectonic-typesetting.github.io):\n"
    "  • Windows : winget install TectonicProject.Tectonic\n"
    "  • macOS   : brew install tectonic\n"
    "  • Linux   : cargo install tectonic  (or your package manager)\n"
    "The .tex was still written, so you can also compile it on Overleaf."
)


class RenderError(RuntimeError):
    """Raised when PDF compilation cannot be completed."""


def tectonic_available() -> bool:
    """True if the ``tectonic`` binary is on PATH."""
    return shutil.which("tectonic") is not None


def count_pdf_pages(pdf_path: Path) -> int:
    """Page count of a PDF (0 if unreadable — callers treat that as 'unknown')."""
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(pdf_path)).pages)
    except Exception as exc:
        logger.debug("Could not count PDF pages: {}", exc)
        return 0


def build_resume_pdf(
    profile: Profile,
    out_path: Path,
    *,
    keep_tex: bool = True,
    one_page: bool = True,
) -> Path:
    """
    Render ``profile`` to a PDF at ``out_path``.

    Recruiters skim a resume in seconds and ATS parsers favor a single page
    for students/early-career, so with ``one_page`` (the default) a result
    that spills past one page is automatically re-rendered in the template's
    compact mode (10pt, tighter margins/spacing). If it *still* overflows, the
    PDF is kept and a warning tells the user what to trim — we never silently
    delete their content.

    Always writes the LaTeX source next to the PDF (``out_path`` with a ``.tex``
    suffix) when ``keep_tex`` is set, so the source is editable/portable.

    Raises
    ------
    RenderError
        If Tectonic is unavailable or the compile fails.
    """
    pdf = compile_tex_to_pdf(render_resume_tex(profile), out_path, keep_tex=keep_tex)
    if not one_page:
        return pdf

    pages = count_pdf_pages(pdf)
    if pages <= 1:
        return pdf

    # Stage 1: same content, denser layout.
    logger.info("Resume is {} pages — retrying in compact one-page mode", pages)
    pdf = compile_tex_to_pdf(render_resume_tex(profile, compact=True), out_path, keep_tex=keep_tex)
    if count_pdf_pages(pdf) <= 1:
        return pdf

    # Stage 2: trim least-relevant content. The tailoring layer orders
    # sections/bullets by relevance, so cutting from the end is principled —
    # and for untailored builds it drops the oldest/last-listed material.
    for level, trimmed in enumerate(_trim_levels(profile), start=1):
        logger.info("Still over one page — trimming (level {})", level)
        pdf = compile_tex_to_pdf(
            render_resume_tex(trimmed, compact=True), out_path, keep_tex=keep_tex
        )
        if count_pdf_pages(pdf) <= 1:
            logger.info("One page achieved at trim level {}", level)
            return pdf

    logger.warning(
        "Resume exceeds one page even after compact layout and trimming. "
        "Consider pruning data/profile.yaml, or pass --job-text so tailoring "
        "selects only the most relevant content."
    )
    return pdf


def _trim_levels(profile: Profile) -> list[Profile]:
    """Progressively trimmed copies of the profile (gentlest first)."""

    def trimmed(
        *,
        bullets: int,
        entries: int,
        projects: int,
        highlights: int,
        skill_groups: int = 99,
        certs: int = 99,
        awards: int = 99,
        publications: int = 99,
        summary_chars: int = 9_999,
    ) -> Profile:
        p = profile.model_copy(deep=True)
        p.experience = p.experience[:entries]
        for xp in p.experience:
            xp.bullets = xp.bullets[:bullets]
        p.projects = p.projects[:projects]
        for pr in p.projects:
            pr.bullets = pr.bullets[: max(1, bullets - 1)]
        for edu in p.education:
            edu.highlights = edu.highlights[:highlights]
        p.skills = p.skills[:skill_groups]
        p.certifications = p.certifications[:certs]
        p.awards = p.awards[:awards]
        p.publications = p.publications[:publications]
        if len(p.basics.summary) > summary_chars:
            p.basics.summary = p.basics.summary[:summary_chars].rsplit(" ", 1)[0] + "…"
        return p

    return [
        trimmed(bullets=3, entries=4, projects=3, highlights=2),
        trimmed(
            bullets=2,
            entries=3,
            projects=2,
            highlights=1,
            skill_groups=6,
            certs=3,
            awards=1,
            publications=1,
        ),
        trimmed(
            bullets=2,
            entries=3,
            projects=1,
            highlights=1,
            skill_groups=4,
            certs=2,
            awards=0,
            publications=0,
            summary_chars=280,
        ),
    ]


def build_cover_letter_pdf(
    profile: Profile,
    paragraphs: list[str],
    out_path: Path,
    *,
    role: str = "",
    company: str = "",
    today: str = "",
    keep_tex: bool = True,
) -> Path:
    """Render a cover letter (profile letterhead + body paragraphs) to a PDF."""
    tex = render_template(
        "coverletter.tex.j2",
        p=profile,
        paragraphs=paragraphs,
        role=role,
        company=company,
        date=today,
    )
    return compile_tex_to_pdf(tex, out_path, keep_tex=keep_tex)


def compile_tex_to_pdf(tex_source: str, out_path: Path, *, keep_tex: bool = True) -> Path:
    """
    Compile a LaTeX source string to a PDF at ``out_path`` with Tectonic.

    Writes the ``.tex`` next to the PDF when ``keep_tex`` is set (portable /
    Overleaf-friendly). Raises :class:`RenderError` if Tectonic is missing or the
    compile fails.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if keep_tex:
        tex_path = out_path.with_suffix(".tex")
        tex_path.write_text(tex_source, encoding="utf-8")
        logger.debug("Wrote LaTeX source | path={}", tex_path)

    tectonic = shutil.which("tectonic")
    if tectonic is None:
        raise RenderError(_INSTALL_HINT)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "doc.tex").write_text(tex_source, encoding="utf-8")
        cmd = [tectonic, "doc.tex", "--outdir", str(tmp_dir), "--chatter", "minimal"]
        logger.info("Compiling PDF with Tectonic | out={}", out_path.name)
        result = subprocess.run(  # noqa: S603 — fixed argv, executable resolved via PATH
            cmd, cwd=tmp_dir, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            msg = f"Tectonic failed (exit {result.returncode}):\n{result.stderr[-1500:]}"
            raise RenderError(msg)

        produced = tmp_dir / "doc.pdf"
        if not produced.is_file():
            raise RenderError("Tectonic reported success but produced no PDF.")
        shutil.copyfile(produced, out_path)

    logger.info("PDF written | path={}", out_path)
    return out_path
