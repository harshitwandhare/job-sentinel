"""
Auth-mode API tests — regression suite for the flow verified live on 2026-06-12:
demo mode = anonymous reads, gated writes, admin-managed accounts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app

if TYPE_CHECKING:
    from pathlib import Path


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> TestClient:
    monkeypatch.setenv("AUTH_MODE", mode)
    app = create_app(
        profile_path=tmp_path / "profile.yaml",
        db_path=tmp_path / "j.db",
        auth_dir=tmp_path,
    )
    return TestClient(app)


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ── AUTH_MODE=off (default local setup) ──────────────────────────────────────


def test_off_mode_everything_open(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch, "off")
    assert client.get("/api/jobs").status_code == 200
    assert client.get("/api/auth/status").json()["mode"] == "off"
    # Writes work without any token.
    assert client.put("/api/profile", json={"basics": {"name": "X"}}).status_code == 200


def test_unknown_mode_falls_back_to_off(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch, "bananas")
    assert client.get("/api/auth/status").json()["mode"] == "off"


# ── AUTH_MODE=demo ───────────────────────────────────────────────────────────


@pytest.fixture
def demo(tmp_path, monkeypatch) -> TestClient:
    client = _client(tmp_path, monkeypatch, "demo")
    # Bootstrap: with no users yet, the first created account is forced admin.
    resp = client.post("/api/auth/users", json={"username": "admin", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["user"]["is_admin"] is True
    return client


def test_demo_reads_are_public(demo: TestClient) -> None:
    assert demo.get("/api/jobs").status_code == 200
    assert demo.get("/api/stats").status_code == 200


def test_demo_writes_need_login(demo: TestClient) -> None:
    assert demo.put("/api/profile", json={"basics": {"name": "X"}}).status_code == 401
    assert demo.post("/api/ops/scrape", json={}).status_code == 401


def test_demo_login_unlocks_writes(demo: TestClient) -> None:
    headers = _login(demo, "admin", "password123")
    resp = demo.put("/api/profile", json={"basics": {"name": "X"}}, headers=headers)
    assert resp.status_code == 200


def test_bad_password_rejected(demo: TestClient) -> None:
    resp = demo.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert resp.status_code == 401


def test_admin_invites_member_but_member_cannot(demo: TestClient) -> None:
    admin = _login(demo, "admin", "password123")
    created = demo.post(
        "/api/auth/users",
        json={"username": "friend", "password": "friendpass123"},
        headers=admin,
    )
    assert created.status_code == 200
    assert created.json()["user"]["is_admin"] is False

    member = _login(demo, "friend", "friendpass123")
    sneaky = demo.post(
        "/api/auth/users",
        json={"username": "sneaky", "password": "sneakypass123"},
        headers=member,
    )
    assert sneaky.status_code == 403


def test_anonymous_cannot_create_users_after_bootstrap(demo: TestClient) -> None:
    resp = demo.post("/api/auth/users", json={"username": "x", "password": "xxxxxxxx"})
    assert resp.status_code == 403


def test_status_reflects_token(demo: TestClient) -> None:
    headers = _login(demo, "admin", "password123")
    body = demo.get("/api/auth/status", headers=headers).json()
    assert body["mode"] == "demo"
    assert body["user"]["username"] == "admin"
    # Garbage token → treated as anonymous, not an error.
    anon = demo.get("/api/auth/status", headers={"Authorization": "Bearer junk"}).json()
    assert anon["user"] is None


# ── AUTH_MODE=required ───────────────────────────────────────────────────────


def test_required_mode_gates_reads_too(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch, "required")
    client.post("/api/auth/users", json={"username": "admin", "password": "password123"})
    assert client.get("/api/jobs").status_code == 401
    headers = _login(client, "admin", "password123")
    assert client.get("/api/jobs", headers=headers).status_code == 200
