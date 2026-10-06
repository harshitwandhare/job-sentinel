"""Tests for the adapter registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.adapters.registry import (
    get_adapter,
    list_adapters,
    load_custom_adapter,
    register_adapter,
)
from job_sentinel.config.settings import ScraperSettings

if TYPE_CHECKING:
    from pathlib import Path


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
    reg._registry.pop("_test_custom", None)


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

    def test_builtin_import_error_is_wrapped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from job_sentinel.adapters import registry as reg

        monkeypatch.setitem(reg._BUILTIN_ADAPTERS, "_broken", "job_sentinel.adapters.sites.nope")
        with pytest.raises(ValueError, match="Failed to load built-in adapter"):
            get_adapter("_broken", ScraperSettings())


_CUSTOM_SRC = """
from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.adapters.registry import register_adapter


class CustomAdapter(SiteAdapter):
    ADAPTER_ID = "_test_custom"
    ADAPTER_NAME = "Custom"
    BASE_URL = "https://example.com"

    def login(self, page):
        pass

    def scrape_page(self, page):
        return []


register_adapter(CustomAdapter)
"""


class TestLoadCustomAdapter:
    def test_loads_and_registers(self, tmp_path: Path) -> None:
        f = tmp_path / "my_adapter.py"
        f.write_text(_CUSTOM_SRC, encoding="utf-8")
        load_custom_adapter(f)
        assert "_test_custom" in list_adapters()
        assert get_adapter("_test_custom", ScraperSettings()).ADAPTER_ID == "_test_custom"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="CUSTOM_ADAPTER_PATH"):
            load_custom_adapter(tmp_path / "absent.py")

    def test_module_that_raises_is_wrapped(self, tmp_path: Path) -> None:
        f = tmp_path / "boom.py"
        f.write_text("raise RuntimeError('bad plugin')", encoding="utf-8")
        with pytest.raises(ValueError, match="bad plugin"):
            load_custom_adapter(f)

    def test_non_python_file_has_no_import_spec(self, tmp_path: Path) -> None:
        f = tmp_path / "adapter.txt"
        f.write_text("x = 1", encoding="utf-8")
        with pytest.raises(ValueError, match="import spec"):
            load_custom_adapter(f)
