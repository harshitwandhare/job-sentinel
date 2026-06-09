"""Document generation — render the profile into ATS-friendly LaTeX/PDF."""

from job_sentinel.documents.coverletter import compose_cover_letter, cover_letter_paragraphs
from job_sentinel.documents.latex import latex_escape, render_resume_tex
from job_sentinel.documents.renderer import (
    RenderError,
    build_cover_letter_pdf,
    build_resume_pdf,
    tectonic_available,
)
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
    "build_cover_letter_pdf",
    "build_resume_pdf",
    "compose_cover_letter",
    "cover_letter_paragraphs",
    "extract_keywords",
    "latex_escape",
    "render_resume_tex",
    "tectonic_available",
]
