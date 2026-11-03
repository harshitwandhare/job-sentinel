"""
core/eligibility.py
───────────────────
Re-read a posting from the applicant-tracking system that actually serves it,
then decide whether the user can apply at all.

Aggregators and community lists carry eligibility flags that go stale in both
directions: roles marked sponsor-friendly that exclude sponsorship in the body
text, and roles marked closed that are still taking applications.  The only
trustworthy copy is the one the employer's own board returns, so every verdict
here quotes the sentence it was based on.

Rendered career pages are JavaScript, so each board is read through its JSON
API instead: Workday CXS, Greenhouse, Lever, Ashby, Workable, SmartRecruiters
and Oracle Recruiting.  Anything unrecognised falls back to stripped HTML.

A verdict is evidence, not a decision.  ``Verdict.blockers`` is what the user
reads before spending twenty minutes on a form; nothing here auto-rejects a
posting on the user's behalf.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

__all__ = ["Rule", "Status", "Verdict", "screen_text", "screen_url"]

_UA = {"User-Agent": "job-sentinel/1.0 (+https://github.com/harshitwandhare/job-sentinel)"}


# ── Verdict model ─────────────────────────────────────────────────────────────


class Status(StrEnum):
    """How confident the screen is that the user may apply."""

    ELIGIBLE = "eligible"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Rule:
    """One named test over the posting text.

    Attributes
    ----------
    name:
        Short slug shown in the UI, e.g. ``"no_sponsorship"``.
    pattern:
        Compiled regex searched against each sentence of the posting.
    explain:
        Plain-English reason shown next to the quoted sentence.
    blocking:
        True when a match means the user cannot apply at all, False when it
        is a caution worth surfacing but not acting on.
    """

    name: str
    pattern: re.Pattern[str]
    explain: str
    blocking: bool = True


@dataclass
class Verdict:
    """Result of screening one posting."""

    status: Status
    blockers: list[tuple[str, str]] = field(default_factory=list)
    cautions: list[tuple[str, str]] = field(default_factory=list)
    title: str = ""
    source: str = ""
    detail: str = ""

    @property
    def summary(self) -> str:
        """One line for a table cell or a CLI row."""
        if self.status is Status.BLOCKED:
            return "; ".join(explain for explain, _ in self.blockers)
        if self.status is Status.UNKNOWN:
            return self.detail or "could not read the posting"
        return "; ".join(explain for explain, _ in self.cautions) or "no blockers found"


# ── Rules ─────────────────────────────────────────────────────────────────────


def _rule(name: str, pattern: str, explain: str, *, blocking: bool = True) -> Rule:
    return Rule(name, re.compile(pattern, re.I), explain, blocking)


#: Ordered so the most decisive reason is reported first.
DEFAULT_RULES: tuple[Rule, ...] = (
    _rule(
        "no_sponsorship",
        r"(will not|does not|do not|unable to|cannot)\s+"
        r"(provide|offer|sponsor|consider)[^.]{0,60}(sponsor|visa)"
        r"|without (requiring|the need for)[^.]{0,40}sponsorship"
        r"|not (require|requiring) sponsorship (now or )?in the future"
        r"|now and in the future"
        r"|authorized to work[^.]{0,60}(independently|without sponsorship)",
        "employer states it will not sponsor a visa",
    ),
    _rule(
        "citizenship",
        r"must be a (u\.?s\.?|united states) citizen"
        r"|u\.?s\.? citizenship (is )?required"
        r"|citizens? only",
        "US citizenship required",
    ),
    _rule(
        "clearance",
        r"security clearance|secret clearance|top secret|polygraph|\bTS/SCI\b",
        "security clearance required",
    ),
    _rule(
        "export_control",
        r"export control|\bITAR\b|\bEAR\b\b|u\.?s\.? person",
        "subject to US export controls, which can stall an offer",
        blocking=False,
    ),
    _rule(
        "undergrad_only",
        r"enrollment in a 4-year undergraduate|undergraduate (students? )?only"
        r"|must be an undergraduate",
        "undergraduate-only programme",
    ),
    _rule(
        "phd_only",
        r"(ph\.?d\.?|doctoral)[^.]{0,40}(required|candidates only)"
        r"|must be (enrolled in|pursuing) a ph\.?d",
        "doctoral candidates only",
    ),
    _rule(
        "underclass_only",
        r"\b(sophomore|freshman|first-year)\b[^.]{0,40}(only|programme|program)"
        r"|rising sophomore",
        "aimed at first or second year students",
        blocking=False,
    ),
)


# ── Board resolution ──────────────────────────────────────────────────────────


def _workday(host: str, path: str) -> str:
    parts = [p for p in path.split("/") if p and p != "en-US"]
    if host.endswith("myworkdaysite.com"):  # /recruiting/<tenant>/<site>/job/...
        tenant, site, rest = parts[1], parts[2], "/".join(parts[3:])
    else:
        tenant, site, rest = host.split(".")[0], parts[0], "/".join(parts[1:])
    return f"https://{host}/wday/cxs/{tenant}/{site}/{rest}"


#: One row per board: host marker, path pattern, kind, and a template whose
#: ``{g1}``/``{g2}`` placeholders take the pattern's capture groups.
_BOARDS: tuple[tuple[str, str, str, str], ...] = (
    (
        "greenhouse.io",
        r"/([^/]+)/jobs/(\d+)",
        "greenhouse",
        "https://boards-api.greenhouse.io/v1/boards/{g1}/jobs/{g2}",
    ),
    (
        "lever.co",
        r"/([^/]+)/([0-9a-f-]{36})",
        "lever",
        "https://api.lever.co/v0/postings/{g1}/{g2}",
    ),
    (
        "ashbyhq.com",
        r"/([^/]+)/([0-9a-f-]{36})",
        "ashby",
        "https://api.ashbyhq.com/posting-api/job-board/{g1}",
    ),
    (
        "smartrecruiters.com",
        r"/([^/]+)/(\d+)",
        "smartrecruiters",
        "https://api.smartrecruiters.com/v1/companies/{g1}/postings/{g2}",
    ),
    (
        "oraclecloud.com",
        r"/job/(\d+)",
        "oracle",
        "https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
        '?finder=ById;Id="{g1}"&expand=all',
    ),
)


def _hosted_at(host: str, domain: str) -> bool:
    """True when *host* is *domain* itself or a subdomain of it.

    A substring test is unsafe: "greenhouse.io" sits inside
    "greenhouse.io.example.net" and "notgreenhouse.io" alike. That matters
    because a posting URL arrives from a community-maintained list anyone can
    open a pull request against, and the Workday and Oracle templates build
    their request URL out of the host they were handed. Matching on the
    registrable suffix keeps a lookalike host from steering a fetch.
    """
    return host == domain or host.endswith(f".{domain}")


def _resolve(url: str) -> tuple[str, str] | None:
    """Return (api_url, board_kind) for *url*, or None when it is unrecognised."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    # hostname, not netloc: it is lower-cased and carries no port or userinfo,
    # so "user@evil.net" and ":8080" cannot smuggle a match past the check.
    host, path = (parsed.hostname or ""), parsed.path

    if _hosted_at(host, "myworkdayjobs.com") or _hosted_at(host, "myworkdaysite.com"):
        return _workday(host, path), "workday"

    for marker, pattern, kind, template in _BOARDS:
        if not _hosted_at(host, marker):
            continue
        match = re.search(pattern, path)
        if match:
            slots = {f"g{i}": g for i, g in enumerate(match.groups(), start=1)}
            return template.format(host=host, **slots), kind
    return None


def _strip(markup: str) -> str:
    """Flatten markup to text.

    Entities are resolved *before* tags are removed: Greenhouse and several
    other boards return HTML that is itself entity-escaped inside the JSON, so
    stripping first would leave ``&lt;p class=...&gt;`` sitting in the output
    and a quoted blocker would be unreadable.
    """
    markup = html.unescape(markup)
    markup = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", markup, flags=re.S | re.I)
    markup = re.sub(r"</(p|div|li|br|tr|h\d)>", "\n", markup, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", markup))


def _unpack(kind: str, body: str) -> tuple[str, str]:
    """Return (title, description_text) for a board response."""
    if kind == "raw":
        return "", _strip(body)

    data: Any = json.loads(body)
    if kind == "workday":
        info = data.get("jobPostingInfo", {})
        return info.get("title", ""), _strip(info.get("jobDescription", ""))
    if kind == "greenhouse":
        return data.get("title", ""), _strip(data.get("content", ""))
    if kind == "lever":
        parts = [data.get("descriptionPlain", "")]
        parts += [f"{s.get('text', '')} {s.get('content', '')}" for s in data.get("lists", [])]
        return data.get("text", ""), _strip(" ".join(parts))
    if kind == "smartrecruiters":
        sections = data.get("jobAd", {}).get("sections", {})
        text = " ".join(str(v.get("text", "")) for v in sections.values() if isinstance(v, dict))
        return data.get("name", ""), _strip(text)
    if kind == "oracle":
        items = data.get("items") or [{}]
        item = items[0]
        return item.get("Title", ""), _strip(item.get("ExternalDescriptionStr", ""))
    if kind == "ashby":
        jobs = data.get("jobs", [])
        first = jobs[0] if jobs else {}
        return first.get("title", ""), _strip(first.get("descriptionHtml", ""))
    return "", _strip(body)


# ── Screening ─────────────────────────────────────────────────────────────────

_SENTENCE = re.compile(r"[^.!?\n]{10,400}[.!?\n]")


def screen_text(text: str, rules: tuple[Rule, ...] = DEFAULT_RULES) -> Verdict:
    """Screen posting *text* against *rules*, quoting the sentence that matched.

    Parameters
    ----------
    text:
        The posting body as plain text.
    rules:
        Tests to apply; defaults to :data:`DEFAULT_RULES`.

    Returns
    -------
    Verdict
        ``UNKNOWN`` when *text* is too short to judge, otherwise ``BLOCKED``
        if any blocking rule matched and ``ELIGIBLE`` if none did.
    """
    if len(text.strip()) < 200:
        return Verdict(Status.UNKNOWN, detail="posting text too short to screen")

    sentences = [s.strip() for s in _SENTENCE.findall(text)]
    verdict = Verdict(Status.ELIGIBLE)
    for rule in rules:
        for sentence in sentences:
            if rule.pattern.search(sentence):
                quote = re.sub(r"\s+", " ", sentence)[:300]
                target = verdict.blockers if rule.blocking else verdict.cautions
                target.append((rule.explain, quote))
                break

    if verdict.blockers:
        verdict.status = Status.BLOCKED
    return verdict


def screen_url(url: str, *, timeout: float = 30.0) -> Verdict:
    """Fetch *url* through its own board API and screen the result.

    Never raises: a transport error or an unreadable board becomes an
    ``UNKNOWN`` verdict carrying the reason in ``detail``.
    """
    resolved = _resolve(url)
    api_url, kind = resolved if resolved else (url, "raw")
    headers = dict(_UA)
    if kind == "oracle":
        headers["REST-Framework-Version"] = "4"

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            body = client.get(api_url).raise_for_status().text
        title, text = _unpack(kind, body)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError) as exc:
        logger.debug("eligibility: {} unreadable via {}: {}", url, kind, exc)
        return Verdict(Status.UNKNOWN, source=kind, detail=f"{type(exc).__name__}: {exc}")

    verdict = screen_text(text)
    verdict.title, verdict.source = title, kind
    return verdict
