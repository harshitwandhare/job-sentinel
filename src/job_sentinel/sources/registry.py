"""
sources/registry.py
────────────────────
Dynamic source registry — mirrors adapters/registry.py.

Built-in sources are lazily loaded from their module paths.
External code can call ``register_source`` to add custom sources.

The registry distinguishes between "all known sources" and
"enabled sources" (those whose SOURCE_ID appears in the
configured enabled_sources list).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from job_sentinel.config.settings import Settings
    from job_sentinel.sources.base import JobSource

# ── Registry store ────────────────────────────────────────────────────────────
_registry: dict[str, type[JobSource]] = {}

# ── Built-in source module paths ──────────────────────────────────────────────
_BUILTIN_SOURCES: dict[str, str] = {
    "remoteok": "job_sentinel.sources.remoteok",
    "themuse": "job_sentinel.sources.themuse",
    "arbeitnow": "job_sentinel.sources.arbeitnow",
    "himalayas": "job_sentinel.sources.himalayas",
    "adzuna": "job_sentinel.sources.adzuna",
    "usajobs": "job_sentinel.sources.usajobs",
    "jobspy": "job_sentinel.sources.jobspy_source",
    "company_board": "job_sentinel.sources.company_boards",
}

# Map source IDs to their class names (for lazy loading)
_SOURCE_CLASS: dict[str, str] = {
    "remoteok": "RemoteOkSource",
    "themuse": "TheMuseSource",
    "arbeitnow": "ArbeitnowSource",
    "himalayas": "HimalayasSource",
    "adzuna": "AdzunaSource",
    "usajobs": "USAJobsSource",
    "jobspy": "JobSpySource",
    "company_board": "CompanyBoardSource",
}


def register_source(source_cls: type[JobSource]) -> None:
    """Register a source class in the global registry.

    Parameters
    ----------
    source_cls:
        A concrete subclass of :class:`JobSource` with a non-empty
        ``SOURCE_ID`` class variable.
    """
    source_id = source_cls.SOURCE_ID
    if not source_id:
        msg = f"Source class {source_cls.__name__} must set SOURCE_ID"
        raise ValueError(msg)
    if source_id in _registry:
        logger.warning("Source '{}' is being re-registered — overwriting", source_id)
    _registry[source_id] = source_cls
    logger.debug("Registered source: '{}'", source_id)


def get_source(source_id: str) -> type[JobSource]:
    """Return the class for the given source ID.

    Lazily loads the built-in module if not yet registered.

    Raises
    ------
    ValueError
        If no source is registered with that ID.
    """
    if source_id not in _registry and source_id in _BUILTIN_SOURCES:
        module_path = _BUILTIN_SOURCES[source_id]
        class_name = _SOURCE_CLASS.get(source_id, "")
        try:
            mod = importlib.import_module(module_path)
            logger.debug("Loaded built-in source module: {}", module_path)
            # Auto-register if the class hasn't registered itself
            if source_id not in _registry and class_name:
                cls = getattr(mod, class_name, None)
                if cls is not None:
                    _registry[source_id] = cls
        except ImportError as exc:
            msg = f"Failed to load built-in source '{source_id}': {exc}"
            raise ValueError(msg) from exc

    if source_id not in _registry:
        available = list(_registry.keys()) + list(_BUILTIN_SOURCES.keys())
        msg = f"Unknown source: '{source_id}'. Available: {sorted(set(available))}."
        raise ValueError(msg)

    return _registry[source_id]


def _instantiate_source(source_id: str, settings: Settings) -> JobSource:
    """Build a source instance, injecting API keys from settings."""
    cls = get_source(source_id)
    src = settings.job_sources

    kwargs: dict[str, Any] = {}
    if source_id == "themuse":
        kwargs = {"api_key": src.themuse_api_key}
    elif source_id == "adzuna":
        kwargs = {
            "app_id": src.adzuna_app_id,
            "app_key": src.adzuna_app_key,
            "country": src.adzuna_country,
        }
    elif source_id == "usajobs":
        kwargs = {"api_key": src.usajobs_api_key, "email": src.usajobs_email}

    return cls(**kwargs)


def build_enabled_sources(settings: Settings) -> list[JobSource]:
    """Instantiate all enabled sources from the settings.

    Sources whose ID is in ``settings.job_sources.enabled_sources`` are
    instantiated with the appropriate API keys.  Sources that fail to
    load (e.g. missing optional extra) are skipped with a warning.
    """
    instances: list[JobSource] = []
    for sid in settings.job_sources.enabled_sources:
        try:
            instance = _instantiate_source(sid, settings)
            instances.append(instance)
            logger.debug("Enabled source: '{}'", sid)
        except Exception as exc:
            logger.warning("Could not load source '{}': {}", sid, exc)

    return instances


def all_sources_status(settings: Settings) -> list[dict[str, Any]]:
    """Return status dicts for every known source.

    Each dict contains:
    ``id``, ``label``, ``enabled``, ``requires_key``,
    ``is_scraper``, ``configured``, ``homepage``.
    """
    enabled_ids = set(settings.job_sources.enabled_sources)
    statuses: list[dict[str, Any]] = []

    for sid in _BUILTIN_SOURCES:
        try:
            instance = _instantiate_source(sid, settings)
            cls = type(instance)
            is_configured = instance.configured()
        except Exception as exc:  # module may not be importable (e.g. jobspy without the extra)
            logger.debug("Could not instantiate source '{}' for status: {}", sid, exc)
            try:
                cls = get_source(sid)
                is_configured = False
            except Exception as inner_exc:
                logger.debug("Could not load source '{}': {}", sid, inner_exc)
                continue

        statuses.append(
            {
                "id": sid,
                "label": cls.LABEL,
                "enabled": sid in enabled_ids,
                "requires_key": cls.requires_key,
                "is_scraper": cls.is_scraper,
                "configured": is_configured,
                "homepage": cls.homepage,
            }
        )

    return statuses


def list_sources() -> list[str]:
    """Return all known source IDs (built-in + registered custom)."""
    return sorted(set(list(_registry.keys()) + list(_BUILTIN_SOURCES.keys())))
