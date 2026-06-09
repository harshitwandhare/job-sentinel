# Branching & releasing

## Branching model — trunk-based with short-lived branches (GitHub Flow)

For a project this size, trunk-based development is the right call (it's also
what most high-velocity teams, including FAANG, actually run under the hood):

- **`main` is always releasable** and always green (every push runs the full CI
  matrix: lint, types, tests, secret scan, supply-chain).
- **Short-lived feature branches** (`feat/…`, `fix/…`, `docs/…`) for anything
  non-trivial, merged via PR once CI is green. Branches live hours-to-days, not
  weeks — no long-running divergent branches to integrate later.
- **Conventional Commits** on every commit; history reads as a changelog.
- No `develop`/release-branch ceremony — that GitFlow overhead doesn't pay for
  itself here. (Revisit only if we ever maintain multiple released majors.)

## Versioning — Semantic Versioning

`MAJOR.MINOR.PATCH`. Pre-1.0, minor bumps may carry breaking changes; once 1.0
ships, SemVer is strict. The version lives in `pyproject.toml`.

## Cutting a release

1. Ensure `main` is green and `CHANGELOG.md`'s `[Unreleased]` section is filled.
2. Bump `version` in `pyproject.toml`.
3. Move `[Unreleased]` → `[X.Y.Z] — YYYY-MM-DD` in `CHANGELOG.md`; add a fresh
   empty `[Unreleased]`.
4. Commit (`chore(release): vX.Y.Z`) and tag:
   ```bash
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```
5. The tag triggers `.github/workflows/release.yml`, which builds the sdist +
   wheel with `uv build` and publishes a GitHub Release with those artifacts.

> PyPI publishing is intentionally deferred until the public API stabilizes; the
> release workflow already produces the distributable artifacts, so wiring a
> trusted-publisher PyPI step later is a one-job addition.
