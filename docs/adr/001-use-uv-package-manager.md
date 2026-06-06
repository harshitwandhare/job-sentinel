# ADR-001: Use uv as Package and Environment Manager

**Status:** Accepted  
**Date:** 2025-01-01  
**Deciders:** Harshit Wandhare  

---

## Context

Python projects need a package manager for:
- Installing and resolving dependencies
- Managing virtual environments
- Pinning exact versions via a lockfile
- Python version management (avoiding pyenv as a separate tool)

Options considered:
1. `pip` + `venv` + `pyenv` (traditional stack)
2. `Poetry` (popular, mature, all-in-one)
3. `uv` (Astral, written in Rust, 2024+)
4. `PDM` (PEP 582, modern)

---

## Decision

Use **`uv`** as the single tool replacing pip, venv, pyenv, and lockfiles.

---

## Rationale

- **Speed**: 10–100× faster installs than pip/poetry. Critical in CI where
  package installs run hundreds of times per day.
- **Simplicity**: Replaces 3–4 tools (pip + venv + pyenv + requirements.txt)
  with one.
- **`pyproject.toml` native**: First-class support for PEP 621 project
  metadata — no separate `poetry.lock` or `Pipfile`.
- **Python version management**: `uv python install 3.11` eliminates pyenv.
- **Open source**: MIT/Apache 2.0 dual license. Even with OpenAI's acquisition
  of Astral (announced March 2026), the license prevents lock-in.
- **Community**: 50K+ GitHub stars as of 2025; used by FastAPI, Pydantic, Ruff.

## Consequences

- Contributors must install `uv` before cloning (one-liner install).
- `uv.lock` is committed for reproducible installs.
- Standard `pip install -e .` still works for contributors who prefer it.

---

## Alternatives Rejected

**Poetry**: Great for library publishing, but slower installs and requires
Python version management via a separate tool.

**pip + pyenv**: Too many moving parts; no lockfile by default.
