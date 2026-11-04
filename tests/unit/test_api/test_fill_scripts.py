"""Tests for the route that serves the browser-filler scripts."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            profile_path=tmp_path / "profile.yaml",
            db_path=tmp_path / "jobs.db",
            auth_dir=tmp_path,
            answers_path=tmp_path / "answers.yaml",
        )
    )


def test_serves_an_adapter(client: TestClient) -> None:
    resp = client.get("/fill/adapters/workday.js")
    assert resp.status_code == 200
    assert "registerAdapter" in resp.text
    assert resp.headers["content-type"].startswith("text/javascript")


def test_serves_the_claude_entry_point(client: TestClient) -> None:
    assert "__jsFill" in client.get("/fill/claude.js").text


@pytest.mark.parametrize(
    "name",
    [
        "../../data/answers.yaml",
        "..%2F..%2Fdata%2Fanswers.yaml",
        "../../.env",
        "nope.js",
    ],
)
def test_nothing_outside_the_filler_directory_is_served(client: TestClient, name: str) -> None:
    """The traversal attempts matter even on a local server: a page in the
    browser can request any URL on it."""
    assert client.get(f"/fill/{name}").status_code == 404


def test_the_test_form_is_served_as_html(client: TestClient) -> None:
    """Served as text/javascript the browser would not render it, and the
    manual test harness would silently be an empty page."""
    resp = client.get("/fill/test-form.html")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_bundle_concatenates_every_adapter(client: TestClient) -> None:
    body = client.get("/fill/bundle.js").text
    for marker in ('id: "workday"', 'id: "greenhouse"', 'id: "lever"', 'id: "ashby"'):
        assert marker in body
    assert body.index('id: "generic"') > body.index('id: "workday"'), (
        "generic must register last so a real adapter always wins"
    )


def test_bundle_is_readable_from_any_origin(client: TestClient) -> None:
    """Greenhouse's CSP blocks a script tag at localhost, so the page fetches
    the bundle instead. It is the repository's own code, never user data."""
    assert client.get("/fill/bundle.js").headers["access-control-allow-origin"] == "*"


def test_minified_bundle_is_smaller_and_still_parses(client: TestClient) -> None:
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path as _Path

    full = client.get("/fill/bundle.js").text
    small = client.get("/fill/bundle.js", params={"min": True}).text
    assert len(small) < len(full)

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    with tempfile.TemporaryDirectory() as tmp:
        path = _Path(tmp) / "bundle.js"
        path.write_text(small, encoding="utf-8")
        result = subprocess.run(
            [node, "--check", str(path)], capture_output=True, text=True, check=False
        )
    assert result.returncode == 0, result.stderr
