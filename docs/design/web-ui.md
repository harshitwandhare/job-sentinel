# Web UI — architecture & plan

**Status:** in progress (branch `feat/web-ui`) · **Owner:** Harshit Wandhare

The CLI is the engine; the web UI is a **thin surface over the same typed core**
via a local HTTP API. Local-first throughout: the API binds to localhost, the
UI runs on your machine, and the optional LLM stays on Ollama. No logic is
duplicated between CLI and UI — both call the same profile/repository/tailor code.

```
 Next.js + shadcn/ui (localhost:3000)
        │  fetch
        ▼
 FastAPI  (localhost:8000)  ──►  job_sentinel core (profile, repo, tailor, render)
                                     │
                                  data/  (profile.yaml, jobs.db)
```

## Backend — FastAPI (this branch, done)

`job_sentinel.api.app` exposes (read-first; mutations land next):

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/api/profile` | full universal profile |
| GET | `/api/profile/summary` | section counts |
| GET | `/api/jobs?limit=` | recent tracked postings |
| POST | `/api/resume/tailor` | tailor profile to a JD → ATS coverage + reordered profile (no side effects) |

- Optional `web` extra: `uv sync --extra web`; run with `job-sentinel serve`
  (or `uvicorn job_sentinel.api.app:app --reload`). Interactive docs at `/docs`.
- CORS limited to local origins. Typed end-to-end; covered by FastAPI TestClient tests.

**Next on the backend:** `PUT /api/profile` (+ per-section CRUD), `POST /api/resume/build`
(returns/stream a PDF), `POST /api/jobs/{id}/status`, and an `--ai` flag on tailor that
routes through the local Ollama `LLMTailor`.

## Frontend — Next.js + shadcn/ui (next phase)

- **Next.js (App Router) + TypeScript + Tailwind + shadcn/ui**, `framer-motion`
  for transitions, a `three.js`/react-three-fiber hero on the landing page.
- Lives in `web/` as a separate workspace (its own `package.json`); the Python
  package stays clean. A typed API client is generated from the FastAPI OpenAPI
  schema (`/openapi.json`) so the UI and backend never drift.
- **Pages:**
  - **Landing** — animated intro, "local-first, your data stays yours" story.
  - **Profile** — Overleaf-style editor for every section (add/edit/reorder
    education, experience, projects, skills, certs); writes back via the API.
  - **Jobs** — tracked postings, deadlines, statuses (new/seen/applied/…).
  - **Résumé studio** — pick a posting → tailor (toggle local-LLM) → live ATS
    coverage + missing keywords → preview/download the PDF.
- Accessibility (WCAG AA) and responsive by default; dark mode.

## Sequencing & standards

- Backend API on this branch → merge via PR with green CI.
- Frontend scaffolded in `web/` next, with its own lint/build CI job and,
  eventually, its own release artifacts.
- Hosting: runs fully local now; the same API backs a future managed tier
  (see [NORTH_STAR](../NORTH_STAR.md)) without changing the core.
