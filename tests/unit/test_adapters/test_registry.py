"""Tests for the adapter registry."""

from __future__ import annotations

import pytest

from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.adapters.registry import get_adapter, list_adapters, register_adapter
from job_sentinel.config.settings import ScraperSettings


class _DummyAdapter(SiteAdapter):
    ADAPTER_ID = "_test_dummy"
    ADAPTER_NAME = "Test Dummy"
    BASE_URL = "https://example.com"

    def login(self, page):  # type: ignore[override]
        pass

    def scrape_page(self, page):  # type: ignore[override]
        return []


@pytest.fixture(autouse=True)
def _clean_registry():
    """Remove test adapter from registry after each test."""
    from job_sentinel.adapters import registry as reg

    yield
    reg._registry.pop("_test_dummy", None)


class TestRegisterAdapter:
    def test_registers_successfully(self) -> None:
        register_adapter(_DummyAdapter)
        assert "_test_dummy" in list_adapters()

    def test_missing_id_raises(self) -> None:
        class _Bad(SiteAdapter):
            ADAPTER_ID = ""

            def login(self, p):
                pass

            def scrape_page(self, p):
                return []

        with pytest.raises(ValueError, match="ADAPTER_ID"):
            register_adapter(_Bad)


class TestGetAdapter:
    def test_returns_instance(self) -> None:
        register_adapter(_DummyAdapter)
        settings = ScraperSettings()
        adapter = get_adapter("_test_dummy", settings)
        assert isinstance(adapter, _DummyAdapter)

    def test_unknown_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown adapter"):
            get_adapter("nonexistent_xyz", ScraperSettings())

    def test_builtin_12twenty_loads(self) -> None:
        settings = ScraperSettings()
        adapter = get_adapter("12twenty", settings)
        assert adapter.ADAPTER_ID == "12twenty"
