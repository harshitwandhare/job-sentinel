"""Tests for the posting eligibility screen."""

from __future__ import annotations

import httpx
import pytest
import respx

from job_sentinel.core.eligibility import Status, screen_text, screen_url

_FILLER = "We build delightful products for millions of customers worldwide. " * 6


def _body(*sentences: str) -> str:
    return _FILLER + " ".join(sentences)


# ── screen_text ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("sentence", "expected_reason"),
    [
        (
            "Must be authorized to work in the US without requiring sponsorship "
            "now or in the future.",
            "employer states it will not sponsor a visa",
        ),
        (
            "Please note that Acme does not provide employment visa sponsorship for this position.",
            "employer states it will not sponsor a visa",
        ),
        (
            "Applicants must be a US citizen to be considered.",
            "US citizenship required",
        ),
        (
            "This role requires an active Top Secret security clearance.",
            "security clearance required",
        ),
        (
            "Enrollment in a 4-year undergraduate degree program is required.",
            "undergraduate-only programme",
        ),
    ],
)
def test_blocking_rules(sentence: str, expected_reason: str) -> None:
    verdict = screen_text(_body(sentence))
    assert verdict.status is Status.BLOCKED
    assert expected_reason in verdict.summary


def test_blocker_quotes_the_sentence_it_judged_on() -> None:
    sentence = "Acme will not sponsor a visa for this internship."
    verdict = screen_text(_body(sentence))
    _, quote = verdict.blockers[0]
    assert "will not sponsor a visa" in quote


def test_clean_posting_is_eligible() -> None:
    verdict = screen_text(
        _body("Currently pursuing a Bachelor's or Master's degree in Computer Science.")
    )
    assert verdict.status is Status.ELIGIBLE
    assert verdict.summary == "no blockers found"


def test_export_control_is_a_caution_not_a_blocker() -> None:
    verdict = screen_text(_body("Some roles are subject to US export control regulations."))
    assert verdict.status is Status.ELIGIBLE
    assert verdict.cautions
    assert "export controls" in verdict.summary


def test_short_text_is_unknown_rather_than_eligible() -> None:
    verdict = screen_text("Software intern.")
    assert verdict.status is Status.UNKNOWN
    assert "too short" in verdict.summary


# ── screen_url ────────────────────────────────────────────────────────────────


@respx.mock
def test_workday_posting_is_read_through_the_cxs_api() -> None:
    page = "https://acme.wd1.myworkdayjobs.com/External/job/Austin/Intern_R1"
    respx.get(
        "https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/External/job/Austin/Intern_R1"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "jobPostingInfo": {
                    "title": "Software Intern",
                    "jobDescription": f"<p>{_body('We will not sponsor a visa.')}</p>",
                }
            },
        )
    )
    verdict = screen_url(page)
    assert verdict.status is Status.BLOCKED
    assert verdict.title == "Software Intern"
    assert verdict.source == "workday"


@respx.mock
def test_greenhouse_entity_escaped_html_is_unescaped_before_quoting() -> None:
    """A quoted blocker must be readable, not a wall of &lt;p class=...&gt;."""
    page = "https://job-boards.greenhouse.io/acme/jobs/4726117006"
    escaped = f"&lt;p&gt;{_body('Acme does not provide employment visa sponsorship.')}&lt;/p&gt;"
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs/4726117006").mock(
        return_value=httpx.Response(200, json={"title": "Intern", "content": escaped})
    )
    _, quote = screen_url(page).blockers[0]
    assert "<p" not in quote
    assert "does not provide employment visa sponsorship" in quote


@respx.mock
def test_unreachable_posting_is_unknown_and_never_raises() -> None:
    page = "https://job-boards.greenhouse.io/acme/jobs/1"
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs/1").mock(
        side_effect=httpx.ConnectError("refused")
    )
    verdict = screen_url(page)
    assert verdict.status is Status.UNKNOWN
    assert "ConnectError" in verdict.detail


@respx.mock
def test_unrecognised_host_falls_back_to_raw_html() -> None:
    page = "https://careers.example.com/jobs/42"
    respx.get(page).mock(
        return_value=httpx.Response(200, text=f"<html><body>{_body('')}</body></html>")
    )
    verdict = screen_url(page)
    assert verdict.source == "raw"
    assert verdict.status is Status.ELIGIBLE
