"""
core/text.py
────────────
Small text-cleaning helpers shared across sources and the résumé engine.

Job descriptions from external sources often arrive as HTML (Himalayas, ATS
boards) or carry URLs. Left raw, the markup and link tokens pollute keyword
extraction and ATS/match scoring (``href``, ``https``, ``h3`` showing up as
"missing keywords"), and read badly in the UI. ``strip_html`` normalises text
once, at the boundary, so everything downstream sees clean prose.

Implemented without regular expressions: tag stripping is a single linear scan
and URL removal is token-based. Over attacker-controlled job text, that avoids
any backtracking/ReDoS risk and keeps the behaviour obvious.
"""

from __future__ import annotations

import html

# Bare-domain TLDs we treat as links. Deliberately omits ambiguous TLDs like
# .net / .ai / .co so skills such as "asp.net" or "node.js" survive.
_LINK_TLDS = (".com", ".org", ".io", ".app", ".dev", ".jobs")


def _strip_tags(text: str) -> str:
    """Remove ``<...>`` tags in one linear pass (no regex → no ReDoS)."""
    out: list[str] = []
    in_tag = False
    for ch in text:
        if ch == "<":
            in_tag = True
        elif ch == ">":
            in_tag = False
            out.append(" ")
        elif not in_tag:
            out.append(ch)
    return "".join(out)


def _is_urlish(token: str) -> bool:
    """True for URL / bare-domain tokens (linear string checks, no regex)."""
    low = token.lower()
    if low.startswith(("http://", "https://", "www.")):
        return True
    # A bare domain like "himalayas.app" — but not "node.js" / "asp.net".
    core = low.rstrip(".,);:")
    return any(core.endswith(tld) for tld in _LINK_TLDS)


def strip_html(text: str) -> str:
    """
    Remove HTML tags, unescape entities, drop URLs/bare domains, and collapse
    whitespace. Returns clean, single-spaced plain text (empty string for falsy
    input). Idempotent — safe to call on already-clean text.
    """
    if not text:
        return ""
    unescaped = html.unescape(_strip_tags(text))
    # str.split() with no args splits on any run of whitespace and drops empties,
    # so this both removes URL tokens and normalises whitespace in one pass.
    return " ".join(tok for tok in unescaped.split() if not _is_urlish(tok))
