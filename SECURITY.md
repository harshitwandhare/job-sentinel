# Security Policy

## Supported versions

Job Sentinel is pre-1.0; security fixes land on `main`.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Report privately
via GitHub Security Advisories ("Report a vulnerability" on the repo's Security
tab), or email the maintainer. You'll get an acknowledgement within a few days
and a fix or mitigation plan as fast as is practical.

## Security model & posture

Job Sentinel is **local-first**. It is designed so sensitive data stays on the
user's machine:

- **Credentials** (portal login, Telegram token) live only in a local `.env`,
  which is git-ignored. They are never logged (loguru `diagnose=False` in file
  sinks) and never sent anywhere except the target service during login.
- **Session cookies** captured by `job-sentinel login` are stored in
  `data/session.json` (git-ignored).
- **Résumé / profile data** stays in local files (`data/profile.yaml`).
- **The optional AI layer is local** (Ollama). No résumé or job text is sent to
  any third-party API by default.

## Automated defenses in CI

- **Secret scanning** — `gitleaks` on every push/PR (blocks committed secrets).
- **Dependency vulnerability scanning** — `pip-audit` (SCA) against the
  dependency set.
- **License compliance** — strong-copyleft (GPL/AGPL) dependencies are blocked
  by a CI gate (`scripts/check_licenses.py`); a third-party license inventory is
  generated.
- **Static analysis** — `ruff` security rules (Bandit-derived `S`) +
  `mypy --strict`.
- **Pre-commit** — `detect-private-key`, large-file and merge-conflict guards,
  plus the above run locally before commits.

## Hardening guidance for self-hosters

- Keep `.env`, `data/`, and `logs/` out of version control (already git-ignored).
- Run the bot under a dedicated, least-privilege OS user.
- Back up `data/` (see the backup notes in the README); it holds your job
  history and profile.
- Re-run `job-sentinel login` rather than storing portal passwords where a
  headless flow would need them.
