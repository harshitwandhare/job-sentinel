"""Document generation — render the profile into ATS-friendly LaTeX/PDF."""

from job_sentinel.documents.latex import latex_escape, render_resume_tex
from job_sentinel.documents.renderer import RenderError, build_resume_pdf, tectonic_available

__all__ = [
    "RenderError",
    "build_resume_pdf",
    "latex_escape",
    "render_resume_tex",
    "tectonic_available",
]
