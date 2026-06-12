"""
Tests for the OpsRunner state machine (api/ops.py): conflict rules, status
snapshots, and worker outcomes — with all browser/scheduler work faked out.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import pytest

import job_sentinel.api.ops as ops_mod
from job_sentinel.api.ops import OpsConflictError, OpsRunner


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> OpsRunner:
    """A fresh runner whose settings load instantly and touch nothing real."""
    fake_settings = SimpleNamespace(
        site_adapter="12twenty",
        scraper=SimpleNamespace(poll_interval_seconds=900),
        session_path=SimpleNamespace(is_file=lambda: False, stat=None),
        custom_adapter_path=None,
    )
    monkeypatch.setattr(ops_mod, "_load_settings", lambda: fake_settings)
    return OpsRunner()


def _wait_until(predicate, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition not met in time")


# ── status() ─────────────────────────────────────────────────────────────────


def test_status_snapshot_shape(runner: OpsRunner) -> None:
    snap = runner.status()
    assert snap["config_ok"] is True
    assert snap["session"] == {"exists": False, "saved_at": None}
    assert snap["login"]["state"] == "idle"
    assert snap["scrape"]["state"] == "idle"
    assert snap["watcher"]["running"] is False
    assert "12twenty" in snap["adapters"]


def test_status_reports_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> None:
        raise ops_mod.OpsConfigError("bad .env")

    monkeypatch.setattr(ops_mod, "_load_settings", boom)
    snap = OpsRunner().status()
    assert snap["config_ok"] is False
    assert "bad .env" in snap["config_error"]


# ── conflict rules ───────────────────────────────────────────────────────────


def test_scrape_conflicts_with_running_scrape(runner: OpsRunner) -> None:
    runner._scrape.state = "running"
    with pytest.raises(OpsConflictError, match="already in progress"):
        runner.start_scrape()


def test_scrape_conflicts_with_running_login(runner: OpsRunner) -> None:
    runner._login.state = "running"
    with pytest.raises(OpsConflictError, match="login"):
        runner.start_scrape()


def test_login_conflicts_with_running_login(runner: OpsRunner) -> None:
    runner._login.state = "running"
    with pytest.raises(OpsConflictError, match="already in progress"):
        runner.start_login()


def test_login_conflicts_with_running_scrape(runner: OpsRunner) -> None:
    runner._scrape.state = "running"
    with pytest.raises(OpsConflictError, match="scrape"):
        runner.start_login()


def test_session_check_conflicts_with_login(runner: OpsRunner) -> None:
    runner._login.state = "running"
    with pytest.raises(OpsConflictError, match="login"):
        runner.check_session()


def test_stop_watcher_when_not_running(runner: OpsRunner) -> None:
    with pytest.raises(OpsConflictError, match="isn't running"):
        runner.stop_watcher()


# ── workers (faked) ──────────────────────────────────────────────────────────


def test_login_worker_success_path(runner: OpsRunner, monkeypatch) -> None:
    events: list[str] = []

    def fake_interactive_login(settings, timeout_seconds, on_event):
        on_event("Credentials prefilled — click Sign In.")
        events.append("logged-in")

    fake_settings = SimpleNamespace(session_path=SimpleNamespace(name="session.json"))
    monkeypatch.setattr(ops_mod, "_load_settings", lambda: fake_settings)
    import job_sentinel.core.session as session_mod

    monkeypatch.setattr(session_mod, "interactive_login", fake_interactive_login)

    runner.start_login(timeout=5)
    _wait_until(lambda: runner._login.state != "running")
    assert runner._login.state == "ok"
    assert events == ["logged-in"]
    assert "session.json" in runner._login.message


def test_login_worker_failure_path(runner: OpsRunner, monkeypatch) -> None:
    import job_sentinel.core.session as session_mod

    def fail(*args, **kwargs):
        raise session_mod.LoginTimeoutError("too slow")

    monkeypatch.setattr(session_mod, "interactive_login", fail)
    runner.start_login(timeout=5)
    _wait_until(lambda: runner._login.state != "running")
    assert runner._login.state == "error"
    assert "signing in" in runner._login.message


def test_scrape_worker_reports_result(runner: OpsRunner, monkeypatch) -> None:
    from job_sentinel.core.models import ScrapeResult

    class FakeScheduler:
        def __init__(self, *a, **k):
            pass

        def run_cycle(self) -> ScrapeResult:
            return ScrapeResult(adapter="12twenty", total_scraped=16, new_count=3)

    class FakeRepo:
        def __init__(self, *a, **k):
            pass

        def close(self) -> None:
            pass

    fake_settings = SimpleNamespace(
        model_copy=lambda update: SimpleNamespace(
            db_path="x",
            telegram=SimpleNamespace(bot_token="t", chat_id="c"),
            dry_run=True,
        )
    )
    monkeypatch.setattr(ops_mod, "_load_settings", lambda: fake_settings)
    import job_sentinel.core.scheduler as sched_mod
    import job_sentinel.db.repository as repo_mod
    import job_sentinel.notifiers.telegram as tg_mod

    monkeypatch.setattr(sched_mod, "Scheduler", FakeScheduler)
    monkeypatch.setattr(repo_mod, "JobRepository", FakeRepo)
    monkeypatch.setattr(
        tg_mod,
        "TelegramNotifier",
        lambda *a, **k: SimpleNamespace(send_new_jobs=lambda jobs: None),
    )

    runner.start_scrape()
    _wait_until(lambda: runner._scrape.state != "running")
    assert runner._scrape.state == "ok"
    assert "3 new" in runner._scrape.message
    assert runner._scrape.detail["total_scraped"] == 16


def test_scrape_worker_surfaces_errors(runner: OpsRunner, monkeypatch) -> None:
    from job_sentinel.core.models import ScrapeResult

    class FailingScheduler:
        def __init__(self, *a, **k):
            pass

        def run_cycle(self) -> ScrapeResult:
            return ScrapeResult(adapter="12twenty", errors=["session expired"])

    fake_settings = SimpleNamespace(
        model_copy=lambda update: SimpleNamespace(
            db_path="x",
            telegram=SimpleNamespace(bot_token="t", chat_id="c"),
            dry_run=True,
        )
    )
    monkeypatch.setattr(ops_mod, "_load_settings", lambda: fake_settings)
    import job_sentinel.core.scheduler as sched_mod
    import job_sentinel.db.repository as repo_mod
    import job_sentinel.notifiers.telegram as tg_mod

    monkeypatch.setattr(sched_mod, "Scheduler", FailingScheduler)
    monkeypatch.setattr(
        repo_mod, "JobRepository", lambda *a, **k: SimpleNamespace(close=lambda: None)
    )
    monkeypatch.setattr(
        tg_mod,
        "TelegramNotifier",
        lambda *a, **k: SimpleNamespace(send_new_jobs=lambda jobs: None),
    )

    runner.start_scrape()
    _wait_until(lambda: runner._scrape.state != "running")
    assert runner._scrape.state == "error"
    assert "log in again" in runner._scrape.message


def test_check_session_delegates(runner: OpsRunner, monkeypatch) -> None:
    import job_sentinel.core.session as session_mod
    from job_sentinel.adapters.base import SessionStatus

    monkeypatch.setattr(
        session_mod,
        "check_session",
        lambda settings: SessionStatus(valid=True, user="Harshit"),
    )
    result = runner.check_session()
    assert result["valid"] is True
    assert result["user"] == "Harshit"


def test_get_runner_is_singleton() -> None:
    ops_mod._runner = None  # reset module state
    a = ops_mod.get_runner()
    b = ops_mod.get_runner()
    assert a is b
    ops_mod._runner = None


def test_status_is_thread_safe_under_concurrent_reads(runner: OpsRunner) -> None:
    errors: list[Exception] = []

    def hammer() -> None:
        try:
            for _ in range(50):
                runner.status()
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=hammer) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
