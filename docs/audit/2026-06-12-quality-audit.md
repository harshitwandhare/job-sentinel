# Quality Audit — 2026-06-12

Scope: full read-only review of the repo (Python core, FastAPI layer, Next.js web UI,
CI/CD, community files) against the bar set by top-tier open-source projects
(httpx/FastAPI/Ruff on the Python side; Next.js ecosystem on the TS side) and the
OpenSSF Scorecard / Best Practices badge criteria. Live web search was unavailable in
this session; external criteria are cited from canonical, stable sources (see
References) and should be re-verified when acting on them.

---

## (a) Scorecard vs. top-tier open source

| Dimension | Grade | Evidence |
|---|---|---|
| Docs (user) | **A-** | Strong README (badges, architecture diagram, quick start), docs/design/{HLD,LLD}.md, adapter-authoring guide, telegram-setup, NORTH_STAR, RELEASING. Gap: `[project.urls].Documentation` points to a GitHub Pages site, but there is **no mkdocs.yml and no docs-deploy workflow**, despite `docs` extras in pyproject — dead link risk. |
| Docs (API reference) | **B** | FastAPI gives /docs for free; no published OpenAPI spec or generated Python API reference. |
| Tests | **B+** | Unit tree mirrors src (15+ modules covered), integration scheduler test, 70% coverage gate, dummy-env CI matrix (3.11/3.12). Gaps: `tests/e2e/` is an empty stub; **zero web UI tests** (no vitest/Playwright); README claims "~82% tests" with no coverage badge backing it. |
| Typing | **A-** | `mypy --strict`, pydantic plugin, `from __future__ import annotations` convention, TS strict typecheck in CI. Gaps: global `ignore_missing_imports = true` weakens strict (the per-module overrides then duplicate it); **no `src/job_sentinel/py.typed` marker**, so downstream users of the package get no types (PEP 561). |
| Lint/format | **A- / D (web)** | Python: ruff with a strong select set incl. S (bandit), PTH, SIM — top-tier. Web: **no ESLint config at all** (package.json has no lint script, no eslint dep); CI only typechecks + builds. |
| CI | **B+** | 6 jobs: lint, mypy, test matrix, gitleaks, pip-audit + license check, web build — broader than most hobby projects. Gaps: **no committed `uv.lock`**, so `uv sync --all-extras` resolves fresh every run → non-reproducible CI and the supply-chain job audits a moving target (uv docs recommend committing the lockfile and using `uv sync --locked` in CI [2]). Actions referenced by tag, not SHA; **no top-level `permissions:` block** (Scorecard Token-Permissions check [1]); gitleaks binary curl'd without checksum verification; no coverage upload/artifact. |
| Security | **B+** | SECURITY.md, gitleaks (CI + pre-commit + .gitleaks.toml), pip-audit, license gate, S-rules in ruff, secrets-aware .gitignore. Gaps: **no dependabot.yml/Renovate** (Scorecard Dependency-Update-Tool check [1]); no OpenSSF Scorecard action or Best Practices badge [3]; npm side has no audit step. |
| Release hygiene | **B+** | CHANGELOG.md (kept current through v0.5.0), conventional commits enforced by pre-commit, release.yml, docs/RELEASING.md, semver-ish tags. Gaps: no signed releases / provenance (Scorecard Signed-Releases [1]); not published to PyPI (fine for now, but `project.urls` implies it). |
| Community files | **C+** | LICENSE (MIT), CONTRIBUTING.md, SECURITY.md, CODEOWNERS, AGENTS.md (excellent, unusual asset). Gaps: **`.github/ISSUE_TEMPLATE/` is an empty directory**, no PR template, **no CODE_OF_CONDUCT.md** — three of GitHub's "community standards" checklist items missing. |
| Dependency hygiene | **B-** | Dev deps duplicated in `[project.optional-dependencies].dev` AND `[tool.uv].dev-dependencies` (drift risk; modern uv convention is `[dependency-groups]`, PEP 735 [2]). Floors are stale for mid-2026: `ruff>=0.4` (pre-commit pins v0.4.8, ~2 years old; `TCH` rules were renamed `TC` in later ruff), mypy v1.10, pre-commit-hooks v4.6. |
| Web stack | **B** | Next 15 + React 19 + Tailwind 3 is current; typed API client (lib/api.ts) mirrors every route — genuinely good parity discipline. Gaps: no eslint (`next lint` / eslint-config-next), no web tests, Tailwind 3 (v4 is current major), three.js/drei hero adds ~heavy deps for a local-first tool. |

**Overall: solid B+.** The Python core is unusually disciplined for a young project
(strict typing, security linting, supply-chain CI, ADRs). The gaps that separate it from
"best in open source" are reproducibility (lockfile), the untested/unlinted web half, and
the missing community/automation files that Scorecard and GitHub community-standards
explicitly measure.

---

## (b) Prioritized backlog

**P0 — correctness & reproducibility**

1. `uv.lock` (new, repo root) — run `uv lock`, commit it, and change all five CI
   `uv sync --all-extras` steps in `.github/workflows/ci.yml` to
   `uv sync --all-extras --locked`. Why: today every CI run and every contributor resolves
   different dependency versions; pip-audit results are non-deterministic. [2]
2. `pyproject.toml` — deduplicate dev deps: keep one source of truth (prefer
   `[dependency-groups].dev`, PEP 735), delete the mirrored list in `[tool.uv]` /
   `[project.optional-dependencies].dev`. Why: the two lists already exist and will drift.
3. `pyproject.toml` `[tool.mypy]` — drop global `ignore_missing_imports = true`; the
   per-module overrides block already handles the four untyped libs. Why: the global flag
   silently masks typo'd imports everywhere, defeating strict mode.
4. `src/job_sentinel/py.typed` (new, empty) + add to hatch wheel includes. Why: PEP 561 —
   without it, `mypy --strict` consumers of the installed package see `Any` for everything.

**P1 — security automation (Scorecard-aligned [1][3])**

5. `.github/dependabot.yml` (new) — ecosystems: `pip` (or `uv` once GA), `npm` (web/),
   `github-actions`. Why: stale floors (ruff 0.4-era) prove updates aren't happening;
   Scorecard Dependency-Update-Tool.
6. `.github/workflows/ci.yml` — add top-level `permissions: contents: read`; pin actions
   to commit SHAs; verify the gitleaks tarball checksum (or use the official
   `gitleaks/gitleaks-action`). Why: Token-Permissions and Pinned-Dependencies checks.
7. `.github/workflows/scorecard.yml` (new) — `ossf/scorecard-action` weekly + badge in
   README. Why: free, continuous measurement of exactly this audit.
8. `.pre-commit-config.yaml` — bump all revs (ruff-pre-commit ≈ v0.4.8 → current; mypy
   mirror; pre-commit-hooks v4.6 → v5+); align hook versions with pyproject floors. Why:
   pre-commit ruff currently enforces an older rule set than CI could.

**P2 — community & docs**

9. `.github/ISSUE_TEMPLATE/` — it exists but is **empty**; add `bug_report.yml`,
   `feature_request.yml`, `config.yml`; add `.github/PULL_REQUEST_TEMPLATE.md`. Why:
   empty template dir looks worse than none; GitHub community standards.
10. `CODE_OF_CONDUCT.md` (new, Contributor Covenant 2.1). Why: required for the OpenSSF
    Best Practices badge and GitHub community profile [3].
11. Docs site: either add `mkdocs.yml` + a Pages deploy workflow (the `docs` extra is
    already declared) or remove the dead `Documentation` URL from `pyproject.toml`.
12. README — replace the hand-written "~82% tests" claim with a real coverage badge
    (Codecov free tier fits the zero-cost constraint) uploaded from the CI test job.

**P3 — web parity with the Python bar**

13. `web/` — add ESLint (`eslint-config-next` flat config) + `npm run lint`, wire into the
    CI `web` job. Why: the Python side has 13 ruff rule families; the TS side has zero lint.
14. `web/` — add a minimal vitest/RTL smoke suite (lib/api.ts request shaping, utils) and,
    later, Playwright e2e against `job-sentinel web`. The empty `tests/e2e/` package is the
    natural home for the latter.
15. `scripts/diagnose_*.py` + `scripts/login_prefill.py` — currently untracked working
    files; either promote the useful ones into `job_sentinel` proper (the `session`/`login`
    commands largely supersede them) or delete. Why: untracked scripts rot and confuse
    contributors.

**P4 — polish**

16. `pyproject.toml` `[tool.pytest.ini_options]` — move `--cov*` addopts out of the default
    (into CI invocation or a `make cov` path). Why: every local `pytest -k one_test` pays
    full coverage + HTML report generation and fails the 70% gate; this is dev-loop friction.
17. CI test job — also run on Python 3.13 (supported by all declared deps in 2026) and add
    `coverage.xml` artifact upload.
18. `release.yml` — add build provenance/attestation (`actions/attest-build-provenance`)
    when PyPI publishing lands; Scorecard Signed-Releases [1].

---

## (c) Token-efficiency notes (repo hygiene for humans and agents)

- **Tracked file count is healthy: 153 files.** No generated artifacts are tracked —
  `htmlcov/` (2.6 MB), `logs/` (1.2 MB), `data/` (954 KB), `web/node_modules`,
  `tsconfig.tsbuildinfo` are all correctly ignored. Good baseline.
- **Local-only clutter that was one `git add -A` away from being committed:**
  `data/diagnostics/` and `data/profile.yaml.bak` were untracked-but-unignored; both are
  now covered by `.gitignore` (appended in this audit pass). The five untracked
  `scripts/diagnose_*.py` / `login_prefill.py` files remain — see backlog #15.
- **pytest default addopts generate `htmlcov/` on every run** — 2.6 MB of HTML rewritten
  each test invocation. Cheap on disk, but agents that glob/grep broadly can waste context
  on it; backlog #16 fixes the root cause. (CLAUDE.md now warns agents off data/, logs/,
  htmlcov/.)
- **Largest hand-written sources** are reasonable: `__main__.py` ~770 lines (largest;
  consider splitting the `resume` sub-app into its own module if it keeps growing),
  `twelve_twenty.py` 496, `api/app.py` 393, `web/lib/api.ts` 373. Nothing pathological.
- `web/package-lock.json` is tracked (correct for `npm ci`), and is the single largest
  tracked file — unavoidable.
- A root `CLAUDE.md` (added in this pass) now carries the layout map, commands, 12twenty
  scrape facts, and conventions, so future agent sessions can skip re-exploration.

---

## References

1. OpenSSF Scorecard checks (Token-Permissions, Pinned-Dependencies,
   Dependency-Update-Tool, Signed-Releases, SAST):
   https://github.com/ossf/scorecard/blob/main/docs/checks.md
2. uv project docs — lockfile and `uv sync --locked` in CI; PEP 735 dependency groups:
   https://docs.astral.sh/uv/concepts/projects/sync/ and https://peps.python.org/pep-0735/
3. OpenSSF Best Practices badge criteria (code of conduct, vulnerability reporting,
   automated test suite): https://www.bestpractices.dev/en/criteria/0
4. PEP 561 — `py.typed` distribution marker: https://peps.python.org/pep-0561/
5. GitHub community standards checklist (issue/PR templates, CoC):
   https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions

*Note: web search was unavailable during this audit; URLs above are canonical/stable but
were cited from prior knowledge (cutoff Jan 2026). Re-verify specifics — e.g., current
ruff version and uv CI flags — before pinning.*
