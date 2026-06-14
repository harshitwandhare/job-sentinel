"""
core/text.py
────────────
Small text-cleaning helpers shared across sources and the résumé engine.

Job descriptions from external sources often arrive as HTML (Himalayas, ATS
boards) or carry URLs. Left raw, the markup and link tokens pollute keyword
extraction and ATS/match scoring (``href``, ``https``, ``h3`` showing up as
"missing keywords"), and read badly in the UI. ``strip_html`` normalises text
once, at the boundary, so everything downstream sees clean prose.
"""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
# URLs and bare domains for the most common TLDs. Deliberately omits ambiguous
# TLDs like .net / .ai / .co so skills such as "asp.net" or "node.js" survive.
_URL_RE = re.compile(
    r"https?://\S+|www\.\S+|\b[\w-]+\.(?:com|org|io|app|dev|jobs)\b",
    re.IGNORECASE,
)
_WS_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """
    Remove HTML tags, unescape entities, drop URLs/bare domains, and collapse
    whitespace. Returns clean, single-spaced plain text (empty string for falsy
    input). Idempotent — safe to call on already-clean text.
    """
    if not text:
        return ""
    no_tags = _TAG_RE.sub(" ", text)
    unescaped = html.unescape(no_tags)
    no_urls = _URL_RE.sub(" ", unescaped)
    return _WS_RE.sub(" ", no_urls).strip()
