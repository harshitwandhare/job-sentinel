"""
documents/latex.py
───────────────────
Turn a :class:`Profile` into a LaTeX source string.

Jinja2 is configured with LaTeX-safe delimiters (``<< >>`` for variables,
``<% %>`` for blocks) so the template can contain literal ``{`` / ``}`` / ``%``
without confusing the engine. All profile-supplied text passes through
``latex_escape`` via the ``|e`` filter, so a stray ``&`` or ``%`` in someone's
job title can never break the build.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, StrictUndefined

if TYPE_CHECKING:
    from job_sentinel.profile.models import Profile

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_RESUME_TEMPLATE = "resume.tex.j2"

# Replacements that don't themselves introduce braces, run after the brace
# rules so we never double-escape the braces inside e.g. \textasciitilde{}.
_LATEX_REPLACEMENTS = [
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
]
# Sentinel for backslash so the rest of the pass doesn't touch the braces in
# its replacement; swapped back in last.
_BACKSLASH_SENTINEL = "\x00"


def latex_escape(value: object) -> str:
    """Escape LaTeX special characters in arbitrary user text."""
    text = "" if value is None else str(value)
    text = text.replace("\\", _BACKSLASH_SENTINEL)
    for old, new in _LATEX_REPLACEMENTS:
        text = text.replace(old, new)
    return text.replace(_BACKSLASH_SENTINEL, r"\textbackslash{}")


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,  # noqa: S701 — LaTeX output, not HTML; escaping is via the |e filter
        undefined=StrictUndefined,
    )
    env.filters["e"] = latex_escape
    return env


def render_resume_tex(profile: Profile, template: str = _RESUME_TEMPLATE) -> str:
    """Render ``profile`` to a LaTeX source string using the named template."""
    env = _build_env()
    return env.get_template(template).render(p=profile)
