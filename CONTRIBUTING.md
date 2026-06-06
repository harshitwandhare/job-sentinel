# Contributing to Job Sentinel

Thank you for your interest in contributing! This guide covers everything
you need to submit high-quality pull requests.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Ways to Contribute](#ways-to-contribute)
3. [Development Setup](#development-setup)
4. [Commit Convention](#commit-convention)
5. [Branch Naming](#branch-naming)
6. [Pull Request Process](#pull-request-process)
7. [Adding a New Portal Adapter](#adding-a-new-portal-adapter)
8. [Tests](#tests)
9. [Style Guide](#style-guide)

---

## Code of Conduct

Be respectful. We follow the
[Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

---

## Ways to Contribute

- 🐛 **Bug reports** — open an Issue with steps to reproduce
- 💡 **Feature requests** — open an Issue describing the use-case
- 🔌 **New portal adapters** — most wanted! See section below
- 📝 **Documentation** — fix typos, improve guides, add examples
- 🧪 **Tests** — increase coverage, add edge cases

---

## Development Setup

```bash
# 1. Fork the repo, then clone your fork
git clone https://github.com/<your-username>/job-sentinel.git
cd job-sentinel

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install all dependencies
uv sync --all-extras

# 4. Install Playwright browser
uv run playwright install chromium

# 5. Install pre-commit hooks (REQUIRED before your first commit)
uv run pre-commit install

# 6. Copy env template
cp .env.example .env
# Fill in at minimum: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
#                     PORTAL_USERNAME, PORTAL_PASSWORD

# 7. Verify everything works
uv run pytest
uv run pre-commit run --all-files
```

---

## Commit Convention

We use **[Conventional Commits](https://conventionalcommits.org)**.
The pre-commit hook enforces this automatically.

Format:
```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

Types:

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no logic change) |
| `refactor` | Code restructuring (no feature/fix) |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system or dependency changes |
| `ci` | CI/CD changes |
| `chore` | Maintenance (version bumps, etc.) |
| `revert` | Reverts a previous commit |

Examples:
```
feat(adapters): add Greenhouse portal adapter
fix(scheduler): handle empty scrape result without crashing
docs(readme): add Docker quick-start section
test(db): add edge case for upsert with APPLIED status
ci: add Python 3.12 to test matrix
```

Breaking changes: append `!` after the type or add `BREAKING CHANGE:` in footer:
```
feat(config)!: rename PORTAL_URL to PORTAL_JOBS_URL
```

---

## Branch Naming

```
feat/<short-description>        # New features
fix/<short-description>         # Bug fixes
docs/<short-description>        # Documentation
refactor/<short-description>    # Refactoring
chore/<short-description>       # Maintenance
```

Examples:
- `feat/greenhouse-adapter`
- `fix/pagination-timeout`
- `docs/adapter-authoring-guide`

---

## Pull Request Process

1. Fork → branch → commit (following convention above)
2. Ensure `uv run pytest` passes with no failures
3. Ensure `uv run pre-commit run --all-files` passes
4. Open a PR against `main` with a clear description
5. Fill in the PR template (auto-populated)
6. At least one maintainer review is required before merge

---

## Adding a New Portal Adapter

This is the most common contribution type. Here's the full process:

### 1. Create the adapter file

```bash
touch src/job_sentinel/adapters/sites/my_portal.py
```

### 2. Implement the interface

```python
from job_sentinel.adapters.base import SiteAdapter
from job_sentinel.adapters.registry import register_adapter
from job_sentinel.core.models import JobPosting
from playwright.sync_api import Page

class MyPortalAdapter(SiteAdapter):
    ADAPTER_ID   = "my_portal"      # unique slug — used in .env
    ADAPTER_NAME = "My Portal"
    BASE_URL     = "https://my-portal.com"

    def login(self, page: Page) -> None:
        # Navigate and authenticate
        ...

    def scrape_page(self, page: Page) -> list[JobPosting]:
        # Extract and return job postings from current page
        ...

    def next_page(self, page: Page) -> bool:
        # Return True if navigated to next page, False if done
        ...

register_adapter(MyPortalAdapter)
```

### 3. Add to the registry

In `src/job_sentinel/adapters/registry.py`, add your adapter to `_BUILTIN_ADAPTERS`:

```python
_BUILTIN_ADAPTERS = {
    "12twenty":  "job_sentinel.adapters.sites.twelve_twenty",
    "handshake": "job_sentinel.adapters.sites.handshake",
    "my_portal": "job_sentinel.adapters.sites.my_portal",   # ← add here
}
```

### 4. Write tests

```bash
touch tests/unit/test_adapters/test_my_portal.py
```

### 5. Update docs

Add an entry in `docs/design/adapter-authoring.md` describing your portal's
login flow and any quirks.

---

## Tests

```bash
# Run all tests
uv run pytest

# Run a specific file
uv run pytest tests/unit/test_db/test_repository.py -v

# Run with coverage report
uv run pytest --cov=job_sentinel --cov-report=html

# Skip slow integration tests
uv run pytest -m "not integration"
```

Test categories:
- `tests/unit/` — fast, no external I/O, no browser
- `tests/integration/` — real SQLite, mocked HTTP
- `tests/e2e/` — requires a real `.env` (run manually, not in CI)

---

## Style Guide

- **Formatter**: `ruff format` (Black-compatible)
- **Linter**: `ruff check` (replaces flake8 + isort + bandit)
- **Type hints**: required on all public functions and methods
- **Docstrings**: Google style for public APIs
- **Line length**: 100 characters
- **Imports**: `from __future__ import annotations` in every file

All of this is enforced automatically by pre-commit + CI.

---

Questions? Open a [Discussion](https://github.com/harshitwandhare/job-sentinel/discussions).
