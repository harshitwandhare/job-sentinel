"""Tests for the shared text cleaner."""

from __future__ import annotations

from job_sentinel.core.text import strip_html


def test_empty_input() -> None:
    assert strip_html("") == ""
    assert strip_html(None) == ""  # type: ignore[arg-type]


def test_removes_tags_and_unescapes_entities() -> None:
    out = strip_html("<h3>Senior</h3> Engineer &amp; lead &lt;ml&gt;")
    assert out == "Senior Engineer & lead <ml>"
    assert "<h3>" not in out


def test_strips_urls_and_bare_domains() -> None:
    out = strip_html("Apply at https://example.com/jobs via himalayas.app or www.foo.com now")
    tokens = out.split()
    # No link-ish tokens survive; surrounding words do.
    assert not any(t.startswith(("http", "www.")) for t in tokens)
    assert "himalayas.app" not in tokens
    assert "www.foo.com" not in tokens
    assert tokens[0] == "Apply" and tokens[-1] == "now"


def test_keeps_dotted_skill_names() -> None:
    # Ambiguous TLDs are intentionally excluded so skills survive.
    tokens = strip_html("Experience with node.js and asp.net required").split()
    assert "node.js" in tokens
    assert "asp.net" in tokens


def test_collapses_whitespace_and_is_idempotent() -> None:
    once = strip_html("<p>a</p>\n\n   <p>b</p>")
    assert once == "a b"
    assert strip_html(once) == once
