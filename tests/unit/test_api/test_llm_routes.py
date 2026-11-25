"""Tests for the LLM settings routes and the .env writer behind them."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point settings at a throwaway .env so no test touches the real one."""
    path = tmp_path / ".env"
    path.write_text("# keep me\nCHAT_BASE_URL=http://localhost:9999/v1\n", encoding="utf-8")
    monkeypatch.setattr("job_sentinel.config.settings._ENV_FILE", str(path))
    return path


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(profile_path=tmp_path / "profile.yaml", db_path=tmp_path / "j.db"))


def test_openapi_schema_can_be_generated(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "LLMConfigPutRequest" in response.json()["components"]["schemas"]


def test_saving_llm_config_reads_the_json_body(client: TestClient, env_file: Path) -> None:
    response = client.put("/api/llm/config", json={"chat": {"model": "llama3.2"}})

    assert response.status_code == 200
    saved = env_file.read_text(encoding="utf-8")
    assert "CHAT_MODEL=llama3.2" in saved
    assert "# keep me" in saved


def test_omitted_base_url_is_left_alone(client: TestClient, env_file: Path) -> None:
    client.put("/api/llm/config", json={"chat": {"model": "llama3.2"}})

    assert "CHAT_BASE_URL=http://localhost:9999/v1" in env_file.read_text(encoding="utf-8")


def test_testing_an_unknown_target_reaches_the_handler(client: TestClient) -> None:
    response = client.post("/api/llm/test", json={"target": "neither"})

    assert response.status_code == 200
    assert response.json()["ok"] is False


@pytest.mark.parametrize("separator", ["\n", "\r", "\u2028"])
def test_value_with_a_line_break_is_rejected(
    client: TestClient, env_file: Path, separator: str
) -> None:
    before = env_file.read_text(encoding="utf-8")
    response = client.put("/api/llm/config", json={"chat": {"model": f"x{separator}INJECTED=1"}})

    assert response.status_code == 422
    assert env_file.read_text(encoding="utf-8") == before
