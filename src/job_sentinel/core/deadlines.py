"""
core/deadlines.py
──────────────────
Best-effort parsing of free-form application-deadline strings.

Portals write deadlines as free text — "06/12/2026, 5:00pm CDT", "June 12, 2026",
"Apply Immediately". We can't parse everything, so we recognise the common,
unambiguous date shapes and return ``None`` otherwise (a posting we can't date
simply isn't flagged as closing soon — never a wrong alarm).

Zero dependencies: a handful of regexes beats pulling in a date library for
text this irregular.
"""

from __future__ import annotations

import re
from datetime import date

_MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
_MONTH_INDEX = {name: i for i, name in enumerate(_MONTHS, start=1)}
_MONTH_INDEX.update({name[:3]: i for i, name in enumerate(_MONTHS, start=1)})

_MDY = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTH_DAY_YEAR = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b")
_DAY_MONTH_YEAR = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(\d{4})\b")


def _month(name: str) -> int | None:
    return _MONTH_INDEX.get(name.lower())


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_deadline(text: str | None) -> date | None:
    """Extract a calendar date from a free-form deadline string, or ``None``."""
    if not text:
        return None

    if m := _MDY.search(text):
        mo, d, y = (int(g) for g in m.groups())
        return _safe_date(y, mo, d)
    if m := _ISO.search(text):
        y, mo, d = (int(g) for g in m.groups())
        return _safe_date(y, mo, d)
    if (m := _MONTH_DAY_YEAR.search(text)) and (month := _month(m.group(1))) is not None:
        return _safe_date(int(m.group(3)), month, int(m.group(2)))
    if (m := _DAY_MONTH_YEAR.search(text)) and (month := _month(m.group(2))) is not None:
        return _safe_date(int(m.group(3)), month, int(m.group(1)))
    return None


def days_until(text: str | None, today: date | None = None) -> int | None:
    """Whole days from ``today`` until the parsed deadline (negative if past)."""
    deadline = parse_deadline(text)
    if deadline is None:
        return None
    return (deadline - (today or date.today())).days


def is_closing_soon(text: str | None, within_days: int, today: date | None = None) -> bool:
    """True if the deadline parses and falls between today and ``within_days`` ahead."""
    n = days_until(text, today)
    return n is not None and 0 <= n <= within_days
