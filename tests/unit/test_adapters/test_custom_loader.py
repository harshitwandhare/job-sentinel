"""Tests for loading an out-of-tree adapter via CUSTOM_ADAPTER_PATH."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from job_sentinel.adapters.registry import list_adapters, load_custom_adapter

if TYPE_CHECKING:
    from pathlib import Path

_ADAPTER_SRC = dedent(
    """
    from job_sentinel.adapters.base import SiteAdapter
    from job_sentinel.adapters.registry import register_adapter


    class _ExternalAdapter(SiteAdapter):
        ADAPTER_ID = "_external_test"
        ADAPTER_NAME = "External Test"
        BASE_URL = "https://example.org"

        def login(self, page):
            pass

        def scrape_page(self, page):
            return []


    register_adapter(_ExternalAdapter)
    """
)


@pytest.fixture(autouse=True)
def _clean_registry():
    yield
    from job_sentinel.adapters import registry as reg

    reg._registry.pop("_external_test", None)


def test_loads_and_registers_external_adapter(tmp_path: Path) -> None:
    adapter_file = tmp_path / "external_adapter.py"
    adapter_file.write_text(_ADAPTER_SRC, encoding="utf-8")

    assert "_external_test" not in list_adapters()
    load_custom_adapter(adapter_file)
    assert "_external_test" in list_adapters()


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_custom_adapter(tmp_path / "nope.py")


def test_broken_module_raises_value_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad_adapter.py"
    bad.write_text("import this_module_does_not_exist_xyz\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Failed to import custom adapter"):
        load_custom_adapter(bad)
