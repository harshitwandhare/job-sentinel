"""Document generation — render the profile into ATS-friendly LaTeX/PDF."""

from job_sentinel.documents.latex import latex_escape, render_resume_tex
from job_sentinel.documents.renderer import RenderError, build_resume_pdf, tectonic_available
from job_sentinel.documents.tailor import (
    KeywordTailor,
    Tailor,
    TailorResult,
    extract_keywords,
)

__all__ = [
    "KeywordTailor",
    "RenderError",
    "Tailor",
    "TailorResult",
    "build_resume_pdf",
    "extract_keywords",
    "latex_escape",
    "render_resume_tex",
    "tectonic_available",
]
