# Job Sentinel

[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13183/badge)](https://www.bestpractices.dev/projects/13183)
[![CI](https://github.com/harshitwandhare/job-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/harshitwandhare/job-sentinel/actions/workflows/ci.yml)

**Local-first career automation, engineered like production software.**

Job Sentinel watches your university job portals, tracks every posting and
deadline, alerts you on Telegram/email, and generates ATS-ready résumés and
cover letters tailored to each role by a **local LLM** — no API keys, no data
leaving your machine.

## Quick start

```bash
pip install job-sentinel
cp .env.example .env          # fill in portal + Telegram credentials
job-sentinel login            # sign in once (credentials prefill from .env)
job-sentinel web --watch      # API + web UI + recurring scrape watcher
```

Open <http://localhost:3000/jobs>.

## What's in these docs

- **[Deployment](deployment.md)** — run the whole stack for $0 (laptop as
  server, Vercel demo, tunnels, optional multi-user auth).
- **[Writing an adapter](design/adapter-authoring.md)** — add a new job portal
  in one file.
- **[High-level design](design/HLD.md)** and **[low-level design](design/LLD.md)**
  — how the scraper, scheduler, DB, notifiers, and resume engine fit together.
- **[North star](NORTH_STAR.md)** — where this project is going: a one-stop
  open-source job-search platform for students.

## Highlights

| | |
|---|---|
| **Scraping** | Pluggable adapters (12twenty, Handshake); API-first capture with DOM fallback; session reuse past Cloudflare |
| **Tracking** | SQLite pipeline (new → seen → applied), deadline radar, keyword filters |
| **Documents** | LaTeX → PDF résumés and cover letters, ATS keyword scoring, local-LLM tailoring, resume PDF import |
| **Surfaces** | CLI, Telegram bot, FastAPI + Next.js web UI — full feature parity |
| **Quality** | 280+ tests (≥80% gate), mypy --strict, ruff, ESLint + vitest, CodeQL, gitleaks, pip-audit, [OpenSSF Best Practices badge](https://www.bestpractices.dev/projects/13183) |
