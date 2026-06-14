# Deployment — everything at $0

Job Sentinel is designed so the **whole stack runs free**. This page is the
honest map of what can run where, and why.

## The one constraint that shapes everything

The scraper **must run on a machine you physically use**:

1. Portal logins (12twenty, Handshake, …) sit behind Cloudflare challenges —
   a human has to clear them in a visible browser once per session
   (`job-sentinel login`; your credentials prefill from `.env`).
2. The saved session (`data/session.json`), the SQLite DB, and Playwright's
   Chromium all live on local disk.

Free cloud tiers (Render, Railway, Fly, Vercel functions) can't do this:
no display for the login, and headless datacenter IPs are exactly what
Cloudflare blocks. So the architecture is **local-first by design**:

| Piece                     | Where it runs        | Cost |
|---------------------------|----------------------|------|
| Scraper + API + DB        | your laptop          | $0   |
| Web UI (your real one)    | your laptop (`job-sentinel web`) | $0 |
| Public demo UI            | Vercel free tier     | $0   |
| Docs site                 | GitHub Pages         | $0   |
| CI (lint, types, tests)   | GitHub Actions free  | $0   |
| Releases (sdist/wheel)    | GitHub Releases      | $0   |
| Alerts                    | Telegram / email     | $0   |
| AI tailoring / extraction | Ollama, local        | $0   |

## One-command install

After cloning the repo, a single script handles everything: Python version
check, virtual-environment creation, `pip install -e ".[web]"`, Playwright
Chromium download, `.env` bootstrap from `.env.example`, and (if Node is
present) `npm install` for the web UI. It is idempotent — safe to re-run.

**macOS / Linux**

```bash
bash scripts/install.sh
```

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

Both scripts end with a next-steps banner covering `job-sentinel login`,
`job-sentinel web`, and the URLs for the API and UI. The optional scraper
extras (`[sources]`, `[apify]`) are *not* installed by default — the scripts
tell you how to add them when needed.

## Your laptop as the server

```bash
# one command: API (FastAPI) + web UI (Next.js) together
job-sentinel web
# or separately:
job-sentinel serve          # API on 127.0.0.1:8000
cd web && npm run dev       # UI on localhost:3000
```

The API binds to `127.0.0.1` by default — nothing is exposed off the machine.

### Sharing your instance with someone (auth)

If you want to expose your instance (e.g. on your LAN, or via a free
[Tailscale](https://tailscale.com) / [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
— both have free personal tiers), turn on authentication first:

```bash
job-sentinel users add yourname --admin     # first account must be --admin
AUTH_MODE=demo job-sentinel serve --host 0.0.0.0
```

- `AUTH_MODE=demo` — anyone can *browse* (read-only demo); actions need a login.
- `AUTH_MODE=required` — everything needs a login.
- Admins create accounts for new users (`job-sentinel users add <name>` or
  `POST /api/auth/users` with an admin token). Passwords are PBKDF2-hashed in
  `data/users.json`; tokens are HMAC-signed and expire after 7 days. No
  external auth service, nothing to pay for.

### Keeping the watcher alive

Run `job-sentinel run` (Telegram bot + scheduler) in a terminal, or register
it as a Windows Scheduled Task / `systemd --user` unit so it starts on boot.
When the portal session expires you'll see scrapes fail — run
`job-sentinel session` to check and `job-sentinel login` to renew (≈ once
every few weeks on 12twenty).

## Public demo on Vercel (free)

The Next.js UI deploys to Vercel's free Hobby tier. Without a reachable API
it renders the marketing pages and empty states — that *is* the restricted
demo. Steps:

1. Import the GitHub repo at vercel.com → framework auto-detects Next.js,
   set the **Root Directory** to `web/`.
2. Set **`NEXT_PUBLIC_DEMO=1`** so every screen is populated with bundled
   sample data (no backend needed) — the public demo then shows the dashboard,
   search, applications, résumé library, AI match, and chat fully alive, with a
   "Live demo — sample data" banner. (Alternatively leave it unset and point
   `NEXT_PUBLIC_API_BASE` at a tunnel to your laptop running `AUTH_MODE=demo`
   for a *live* demo over your real data.)

Every push to `main` auto-deploys — that's the CD half, free.

## Docs on GitHub Pages (free)

`mkdocs.yml` is already configured (`docs` extra). The Docs workflow builds
and publishes the site through the GitHub Pages artifact flow on every push
to `main` that touches `docs/` — no `gh-pages` branch involved (a branch
push would also trigger a doomed Vercel preview build). Preview locally with:

```bash
uv run mkdocs serve
```

## CI/CD (GitHub Actions, free for public repos)

- `ci.yml` — ruff, mypy, pytest with coverage gate on every push/PR.
- `release.yml` — push a tag (`git tag v0.6.0 && git push origin v0.6.0`) and
  it builds the sdist/wheel and creates the GitHub Release automatically
  (publishes to PyPI too once a `PYPI_API_TOKEN` secret exists).
