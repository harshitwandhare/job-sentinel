"""
HTTP mapping for the /api/ops/* routes: success payloads, 409 on a busy runner,
503 on a bad .env. The runner itself is covered in test_ops.py, so it is faked here.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app
from job_sentinel.api.ops import OpsConfigError, OpsConflictError

if TYPE_CHECKING:
    from pathlib import Path

# `job_sentinel.api.app` is shadowed by the `app` attribute on the package.
app_mod = importlib.import_module("job_sentinel.api.app")


class FakeRunner:
    """Records calls; raises `error` from every action when one is set."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, Any]] = []

    def _act(self, name: str, arg: Any = None) -> None:
        self.calls.append((name, arg))
        if self.error:
            raise self.error

    def status(self) -> dict[str, Any]:
        return {"watcher": {"running": False}}

    def start_login(self, timeout: int = 300) -> None:
        self._act("login", timeout)

    def check_session(self) -> dict[str, Any]:
        self._act("check")
        return {"valid": True}

    def start_scrape(self, *, send: bool = False) -> None:
        self._act("scrape", send)

    def start_watcher(self) -> None:
        self._act("watch_start")

    def stop_watcher(self) -> None:
        self._act("watch_stop")


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runner: FakeRunner) -> TestClient:
    monkeypatch.setenv("AUTH_MODE", "off")
    monkeypatch.setattr(app_mod, "get_runner", lambda: runner)
    app = create_app(
        profile_path=tmp_path / "profile.yaml",
        db_path=tmp_path / "j.db",
        auth_dir=tmp_path,
    )
    return TestClient(app)


def test_status_returns_runner_snapshot(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch, FakeRunner())
    assert client.get("/api/ops/status").json() == {"watcher": {"running": False}}


def test_actions_forward_arguments_and_report_success(tmp_path, monkeypatch) -> None:
    runner = FakeRunner()
    client = _client(tmp_path, monkeypatch, runner)

    assert client.post("/api/ops/login", json={"timeout": 120}).json() == {"started": True}
    assert client.post("/api/ops/session/check").json() == {"valid": True}
    assert client.post("/api/ops/scrape", json={"send": True}).json() == {"started": True}
    assert client.post("/api/ops/watcher/start").json() == {"running": True}
    assert client.post("/api/ops/watcher/stop").json() == {"running": False}

    assert runner.calls == [
        ("login", 120),
        ("check", None),
        ("scrape", True),
        ("watch_start", None),
        ("watch_stop", None),
    ]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/ops/login", {}),
        ("post", "/api/ops/session/check", None),
        ("post", "/api/ops/scrape", {}),
        ("post", "/api/ops/watcher/start", None),
        ("post", "/api/ops/watcher/stop", None),
    ],
)
def test_busy_runner_maps_to_409(tmp_path, monkeypatch, method, path, body) -> None:
    client = _client(tmp_path, monkeypatch, FakeRunner(OpsConflictError("busy")))
    resp = getattr(client, method)(path, json=body) if body is not None else client.post(path)
    assert resp.status_code == 409
    assert "another job is in progress" in resp.json()["detail"]


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/ops/login", {}),
        ("/api/ops/session/check", None),
        ("/api/ops/scrape", {}),
        ("/api/ops/watcher/start", None),
    ],
)
def test_bad_env_maps_to_503(tmp_path, monkeypatch, path, body) -> None:
    client = _client(tmp_path, monkeypatch, FakeRunner(OpsConfigError("bad .env")))
    resp = client.post(path, json=body) if body is not None else client.post(path)
    assert resp.status_code == 503
    assert ".env" in resp.json()["detail"]
