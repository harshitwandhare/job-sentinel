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

from job_sentinel.documents.latex import render_resume_tex

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


def build_resume_pdf(
    profile: Profile,
    out_path: Path,
    *,
    keep_tex: bool = True,
) -> Path:
    """
    Render ``profile`` to a PDF at ``out_path``.

    Always writes the LaTeX source next to the PDF (``out_path`` with a ``.tex``
    suffix) when ``keep_tex`` is set, so the source is editable/portable.

    Raises
    ------
    RenderError
        If Tectonic is unavailable or the compile fails.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tex_source = render_resume_tex(profile)

    if keep_tex:
        tex_path = out_path.with_suffix(".tex")
        tex_path.write_text(tex_source, encoding="utf-8")
        logger.debug("Wrote LaTeX source | path={}", tex_path)

    tectonic = shutil.which("tectonic")
    if tectonic is None:
        raise RenderError(_INSTALL_HINT)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "resume.tex").write_text(tex_source, encoding="utf-8")
        cmd = [tectonic, "resume.tex", "--outdir", str(tmp_dir), "--chatter", "minimal"]
        logger.info("Compiling resume with Tectonic")
        result = subprocess.run(  # noqa: S603 — fixed argv, executable resolved via PATH
            cmd, cwd=tmp_dir, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            msg = f"Tectonic failed (exit {result.returncode}):\n{result.stderr[-1500:]}"
            raise RenderError(msg)

        produced = tmp_dir / "resume.pdf"
        if not produced.is_file():
            raise RenderError("Tectonic reported success but produced no PDF.")
        shutil.copyfile(produced, out_path)

    logger.info("Resume PDF written | path={}", out_path)
    return out_path
