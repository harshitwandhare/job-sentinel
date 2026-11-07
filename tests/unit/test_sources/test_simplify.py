"""Tests for the Simplify GitHub list source."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.sources.base import JobQuery
from job_sentinel.sources.simplify import LISTS, SimplifySource

_README = """
<table>
<tr>
<td>🔥 <strong><a href="https://simplify.jobs/c/Acme">Acme</a></strong></td>
<td>Software Engineer Intern 🎓</td>
<td>Austin, TX</td>
<td><a href="https://acme.wd1.myworkdayjobs.com/job/123?utm_source=Simplify&ref=Simplify">Apply</a></td>
<td>1d</td>
</tr>
<tr>
<td>↳</td>
<td>ML Engineer Intern</td>
<td>Remote in USA</td>
<td><a href="https://acme.wd1.myworkdayjobs.com/job/456?utm_source=Simplify&ref=Simplify">Apply</a></td>
<td>3d</td>
</tr>
<tr>
<td><strong><a href="https://simplify.jobs/c/Globex">Globex</a></strong></td>
<td>Backend Intern</td>
<td>NYC</td>
<td>🔒 <a href="https://globex.com/job/9?utm_source=Simplify&ref=Simplify">Apply</a></td>
<td>2d</td>
</tr>
<tr>
<td><strong><a href="https://simplify.jobs/c/Initech">Initech</a></strong></td>
<td>Data Intern</td>
<td>Boston, MA</td>
<td><a href="https://initech.com/job/7?utm_source=Simplify&ref=Simplify">Apply</a></td>
<td>2mo</td>
</tr>
</table>
"""


def _mock() -> None:
    respx.get(LISTS["summer2027"]).mock(return_value=httpx.Response(200, text=_README))


@respx.mock
def test_parses_rows_and_carries_company_forward() -> None:
    _mock()
    out = SimplifySource().search(JobQuery())
    assert [p.employer for p in out] == ["Acme", "Acme", "Initech"]
    assert out[0].title == "Software Engineer Intern"
    assert out[1].employer == "Acme", "the ↳ row must inherit the previous company"
    assert out[1].title == "ML Engineer Intern"


@respx.mock
def test_keeps_rows_whose_link_already_has_a_query_string() -> None:
    readme = """
    <tr>
    <td><strong>Waymo</strong></td>
    <td>Software Engineering Intern</td>
    <td>Mountain View, CA</td>
    <td><a href="https://careers.withwaymo.com/jobs?gh_jid=835&utm_source=Simplify&ref=Simplify">Apply</a></td>
    <td>1d</td>
    </tr>
    """
    respx.get(LISTS["summer2027"]).mock(return_value=httpx.Response(200, text=readme))
    out = SimplifySource().search(JobQuery())
    assert [p.portal_url for p in out] == ["https://careers.withwaymo.com/jobs?gh_jid=835"]


@respx.mock
def test_skips_closed_rows() -> None:
    _mock()
    employers = {p.employer for p in SimplifySource().search(JobQuery())}
    assert "Globex" not in employers, "a locked row is closed and must be dropped"


@respx.mock
def test_sorted_newest_first_and_dates_derived_from_age() -> None:
    _mock()
    out = SimplifySource().search(JobQuery())
    ages = [p.raw_data["age_days"] for p in out]
    assert ages == sorted(ages)
    assert ages[-1] == 60, "'2mo' should resolve to 60 days"
    assert out[0].posted_date > out[-1].posted_date


@respx.mock
def test_date_posted_days_filter() -> None:
    _mock()
    out = SimplifySource().search(JobQuery(date_posted_days=2))
    assert [p.raw_data["age_days"] for p in out] == [1]


@respx.mock
def test_remote_and_keyword_filters() -> None:
    _mock()
    remote = SimplifySource().search(JobQuery(remote=True))
    assert [p.title for p in remote] == ["ML Engineer Intern"]
    matched = SimplifySource().search(JobQuery(keywords="software engineer"))
    assert [p.title for p in matched] == ["Software Engineer Intern"]


@respx.mock
def test_posting_ids_are_namespaced_and_stable() -> None:
    _mock()
    first = SimplifySource().search(JobQuery())[0]
    again = SimplifySource().search(JobQuery())[0]
    assert first.posting_id.startswith("simplify:summer2027:")
    assert first.posting_id == again.posting_id


@respx.mock
def test_network_failure_returns_empty_not_raise() -> None:
    respx.get(LISTS["summer2027"]).mock(side_effect=httpx.ConnectError("down"))
    assert SimplifySource().search(JobQuery()) == []


def test_unknown_list_slug_is_dropped() -> None:
    assert SimplifySource(lists=("summer2027", "nope")).lists == ("summer2027",)
