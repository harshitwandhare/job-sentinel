"""
adapters/registry.py
─────────────────────
Dynamic adapter registry — discovers and instantiates site adapters by ID.

How it works
────────────
1.  Every built-in adapter in ``adapters/sites/`` is imported here once
    at module load.  Each adapter calls ``register()`` on import via its
    module-level ``__init_adapter__`` pattern — or just by being listed
    in ``_BUILTIN_ADAPTERS`` below.

2.  Users can register a custom adapter at runtime by calling
    ``register_adapter(MyAdapter)`` before ``get_adapter()`` is called.

3.  ``get_adapter(adapter_id, settings)`` returns a ready-to-use instance.

Adding a new built-in adapter
──────────────────────────────
1.  Create ``src/job_sentinel/adapters/sites/my_site.py``
2.  Subclass :class:`~job_sentinel.adapters.base.SiteAdapter`
3.  Set ``ADAPTER_ID = "my_site"``
4.  Add ``"my_site"`` to ``_BUILTIN_ADAPTERS`` in this file
5.  That's it — no other code changes needed
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from job_sentinel.adapters.base import SiteAdapter
    from job_sentinel.config.settings import ScraperSettings

# ── Registry store ────────────────────────────────────────────────────────────
_registry: dict[str, type[SiteAdapter]] = {}

# ── Built-in adapter module paths ─────────────────────────────────────────────
# Add new adapters here — just the ID string, module path is inferred.
_BUILTIN_ADAPTERS: dict[str, str] = {
    "12twenty": "job_sentinel.adapters.sites.twelve_twenty",
    "handshake": "job_sentinel.adapters.sites.handshake",
}


def register_adapter(adapter_cls: type[SiteAdapter]) -> None:
    """
    Register an adapter class in the global registry.

    Parameters
    ----------
    adapter_cls:
        A concrete subclass of :class:`SiteAdapter` with a non-empty
        ``ADAPTER_ID`` class variable.

    Raises
    ------
    ValueError
        If ``ADAPTER_ID`` is not set or conflicts with an existing entry.
    """
    adapter_id = adapter_cls.ADAPTER_ID
    if not adapter_id:
        msg = f"Adapter class {adapter_cls.__name__} must set ADAPTER_ID"
        raise ValueError(msg)
    if adapter_id in _registry:
        logger.warning("Adapter '{}' is being re-registered — overwriting", adapter_id)
    _registry[adapter_id] = adapter_cls
    logger.debug("Registered adapter: '{}'", adapter_id)


def get_adapter(adapter_id: str, scraper_settings: ScraperSettings) -> SiteAdapter:
    """
    Return an instantiated adapter for the given ``adapter_id``.

    Lazily loads built-in adapters on first access.

    Parameters
    ----------
    adapter_id:
        The adapter slug (e.g. ``"12twenty"``).
    scraper_settings:
        Passed through to the adapter constructor.

    Raises
    ------
    ValueError
        If no adapter is registered with that ID.
    """
    # Lazy-load the built-in module if not yet registered
    if adapter_id not in _registry and adapter_id in _BUILTIN_ADAPTERS:
        module_path = _BUILTIN_ADAPTERS[adapter_id]
        try:
            importlib.import_module(module_path)
            logger.debug("Loaded built-in adapter module: {}", module_path)
        except ImportError as exc:
            msg = f"Failed to load built-in adapter '{adapter_id}': {exc}"
            raise ValueError(msg) from exc

    if adapter_id not in _registry:
        available = list(_registry.keys()) + list(_BUILTIN_ADAPTERS.keys())
        msg = (
            f"Unknown adapter: '{adapter_id}'. "
            f"Available: {sorted(set(available))}. "
            f"See docs/design/adapter-authoring.md to create a new one."
        )
        raise ValueError(msg)

    cls = _registry[adapter_id]
    return cls(scraper_settings)


def load_custom_adapter(path: Path) -> None:
    """
    Import an out-of-tree adapter file so it can self-register.

    Lets users keep a private adapter outside the package tree and point at it
    with ``CUSTOM_ADAPTER_PATH`` in their ``.env`` — no fork required. The file
    is expected to call :func:`register_adapter` at module level (the same
    pattern every built-in adapter uses).

    Parameters
    ----------
    path:
        Filesystem path to a ``.py`` file defining and registering a
        :class:`SiteAdapter` subclass.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not point at an existing file.
    ValueError
        If the module cannot be loaded or executed.
    """
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        msg = f"CUSTOM_ADAPTER_PATH does not exist: {path}"
        raise FileNotFoundError(msg)

    module_name = f"job_sentinel.adapters.custom.{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        msg = f"Could not build an import spec for custom adapter: {path}"
        raise ValueError(msg)

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        msg = f"Failed to import custom adapter '{path}': {exc}"
        raise ValueError(msg) from exc

    logger.info("Loaded custom adapter from {}", path)


def list_adapters() -> list[str]:
    """Return all registered adapter IDs (built-in + custom)."""
    return sorted(set(list(_registry.keys()) + list(_BUILTIN_ADAPTERS.keys())))
