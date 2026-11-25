"""Tests for the posting eligibility screen."""

from __future__ import annotations

import httpx
import pytest
import respx

from job_sentinel.core.eligibility import Status, _resolve, _unpack, screen_text, screen_url

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


@pytest.mark.parametrize(
    "url",
    [
        "https://greenhouse.io.attacker.net/acme/jobs/1",
        "https://notgreenhouse.io/acme/jobs/1",
        "https://acme.wd1.myworkdayjobs.com.attacker.net/External/job/A/B",
        "https://ehtl.fa.us6.oraclecloud.com.attacker.net/hcmUI/x/job/19816",
        "ftp://boards-api.greenhouse.io/acme/jobs/1",
    ],
)
def test_lookalike_host_is_not_treated_as_a_known_board(url: str) -> None:
    """A host that merely contains a board's domain must not steer the fetch.

    Posting URLs come from a list anyone can open a pull request against, and
    the Workday and Oracle templates build their request URL from the host.
    """
    assert _resolve(url) is None


@pytest.mark.parametrize(
    ("url", "kind"),
    [
        ("https://job-boards.greenhouse.io/acme/jobs/1", "greenhouse"),
        ("https://boards.greenhouse.io/acme/jobs/1", "greenhouse"),
        ("https://acme.wd1.myworkdayjobs.com/External/job/A/B", "workday"),
        ("https://ehtl.fa.us6.oraclecloud.com/hcmUI/x/job/19816", "oracle"),
        ("https://jobs.smartrecruiters.com/Acme/744000159218439", "smartrecruiters"),
    ],
)
def test_real_board_hosts_still_resolve(url: str, kind: str) -> None:
    resolved = _resolve(url)
    assert resolved is not None
    assert resolved[1] == kind


@respx.mock
def test_unrecognised_host_falls_back_to_raw_html() -> None:
    page = "https://careers.example.com/jobs/42"
    respx.get(page).mock(
        return_value=httpx.Response(200, text=f"<html><body>{_body('')}</body></html>")
    )
    verdict = screen_url(page)
    assert verdict.source == "raw"
    assert verdict.status is Status.ELIGIBLE


# ── visa class, which is a different question from sponsorship ────────────────

_EXCLUSION = "programme excludes F-1 students outright"


@pytest.mark.parametrize(
    "sentence",
    [
        # The clause that cost a real application: the employer sponsors, but
        # the programme excludes the visa class regardless.
        "Individuals on temporary visa classifications, including E, F-1 (CPT or OPT), "
        "H-1, H-2, L, B, J, or TN, are not eligible for the Program.",
        "Applicants on an F-1 visa are not eligible for this internship.",
        "Students are not eligible for this programme if they hold F-1 status.",
        "We do not accept CPT candidates for this role.",
    ],
)
def test_visa_class_exclusion_blocks(sentence: str) -> None:
    verdict = screen_text(_body(sentence))
    assert verdict.status is Status.BLOCKED
    assert _EXCLUSION in verdict.summary


@pytest.mark.parametrize(
    "sentence",
    [
        # F-1 named welcomingly is the opposite of an exclusion, and treating
        # it as one would hide exactly the roles worth applying to.
        "We welcome all work authorization types, including F-1 students using OPT or STEM OPT.",
        "Work authorization including F-1 OPT is accepted; we review all candidates.",
        "We hire interns from many backgrounds and sponsor where required.",
        # "not eligible" about something else entirely.
        "The optional essay is not eligible for extra credit.",
    ],
)
def test_visa_class_rule_does_not_fire_on_welcoming_or_unrelated_text(sentence: str) -> None:
    verdict = screen_text(_body(sentence))
    assert _EXCLUSION not in verdict.summary


def test_a_posting_can_sponsor_and_still_exclude_the_visa_class() -> None:
    """The two rules answer different questions, so neither substitutes for the
    other. This posting sponsors and is still a hard stop."""
    sentence = (
        "We are happy to sponsor visas for full-time roles. Individuals on temporary visa "
        "classifications are not eligible for the internship Program."
    )
    verdict = screen_text(_body(sentence))
    assert verdict.status is Status.BLOCKED
    assert _EXCLUSION in verdict.summary


@pytest.mark.parametrize(
    ("kind", "payload", "title", "needle"),
    [
        (
            "lever",
            {
                "text": "Data Intern",
                "descriptionPlain": "Join the data team.",
                "lists": [{"text": "Requirements", "content": "<li>Must be a US citizen</li>"}],
            },
            "Data Intern",
            "Must be a US citizen",
        ),
        (
            "smartrecruiters",
            {
                "name": "Analyst Intern",
                "jobAd": {"sections": {"qualifications": {"text": "<p>Python</p>"}, "bad": 3}},
            },
            "Analyst Intern",
            "Python",
        ),
        (
            "oracle",
            {"items": [{"Title": "ML Intern", "ExternalDescriptionStr": "<p>Train models</p>"}]},
            "ML Intern",
            "Train models",
        ),
        (
            "ashby",
            {"jobs": [{"title": "SWE Intern", "descriptionHtml": "<p>Build things</p>"}]},
            "SWE Intern",
            "Build things",
        ),
    ],
)
def test_board_payloads_are_flattened_to_title_and_text(
    kind: str, payload: dict, title: str, needle: str
) -> None:
    import json

    got_title, text = _unpack(kind, json.dumps(payload))
    assert got_title == title
    assert needle in text
    assert "<" not in text


@pytest.mark.parametrize(
    ("kind", "payload"),
    [("oracle", {"items": []}), ("oracle", {}), ("ashby", {"jobs": []})],
)
def test_empty_board_responses_unpack_to_blank_text(kind: str, payload: dict) -> None:
    import json

    assert _unpack(kind, json.dumps(payload)) == ("", "")


# -- degree level stated in the title -----------------------------------------

_UNDERGRAD = "undergraduate-only programme"
_PHD = "doctoral candidates only"


def _screen_listed(title: str) -> str:
    """Screen a clean posting body listed under *title* on an unknown host."""
    page = "https://careers.example.com/jobs/7"
    respx.get(page).mock(return_value=httpx.Response(200, text=f"<p>{_body('')}</p>"))
    return screen_url(page, title=title).summary


@respx.mock
@pytest.mark.parametrize(
    ("title", "reason"),
    [
        ("Campus Undergraduate Summer Internship Program - Software Engineer 2027", _UNDERGRAD),
        ("Software Engineering Intern (Undergraduate)", _UNDERGRAD),
        ("Under-graduate Co-op, Platform", _UNDERGRAD),
        ("PhD Research Intern, Machine Learning", _PHD),
        ("Doctoral Internship - Optimisation", _PHD),
    ],
)
def test_title_alone_can_block(title: str, reason: str) -> None:
    assert _screen_listed(title) == reason


@respx.mock
@pytest.mark.parametrize(
    "title",
    [
        "Software Intern (Undergraduate or Graduate)",
        "Undergraduate/Master's Software Engineering Intern",
        "Undergraduate and MS Internship",
        "Undergraduate & Postgraduate Summer Program",
        "MS/PhD Research Intern",
        "PhD or Master's Intern, Applied Science",
        "Software Engineer, Undergraduate Admissions Systems",
        "Research Engineer, PhD",
        "Junior Software Engineer Intern",
        "Graduate Software Engineering Program",
    ],
)
def test_title_rules_leave_other_titles_alone(title: str) -> None:
    assert _screen_listed(title) == "no blockers found"


@respx.mock
def test_board_title_is_screened_and_quoted() -> None:
    page = "https://job-boards.greenhouse.io/acme/jobs/2"
    respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs/2").mock(
        return_value=httpx.Response(
            200, json={"title": "Undergraduate Intern", "content": _body("")}
        )
    )
    verdict = screen_url(page)
    assert verdict.status is Status.BLOCKED
    assert verdict.blockers == [(_UNDERGRAD, "Undergraduate Intern")]


@respx.mock
def test_title_does_not_repeat_a_blocker_the_body_already_gave() -> None:
    page = "https://careers.example.com/jobs/8"
    body = _body("You must be an undergraduate to apply.")
    respx.get(page).mock(return_value=httpx.Response(200, text=f"<p>{body}</p>"))
    verdict = screen_url(page, title="Undergraduate Intern")
    assert [explain for explain, _ in verdict.blockers] == [_UNDERGRAD]


@respx.mock
def test_title_still_blocks_when_the_posting_cannot_be_read() -> None:
    page = "https://careers.example.com/jobs/9"
    respx.get(page).mock(side_effect=httpx.ConnectError("refused"))
    verdict = screen_url(page, title="Undergraduate Summer Internship")
    assert verdict.status is Status.BLOCKED
