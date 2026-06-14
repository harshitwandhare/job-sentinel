# Web UI — architecture & page inventory

**Status:** live · **Owner:** Harshit Wandhare

The CLI is the engine; the web UI is a **thin surface over the same typed core**
via a local HTTP API. Local-first throughout: the API binds to localhost, the
UI runs on your machine, and the optional LLM stays on Ollama or whichever
provider you configure. No logic is duplicated between CLI and UI — both call
the same profile/repository/tailor/match code.

```
 Next.js 15 + Tailwind (localhost:3000)
        │  fetch (lib/api.ts — typed client)
        ▼
 FastAPI  (localhost:8000)  ──►  job_sentinel core
                                  (profile, repo, sources, match, tailor, render)
                                     │
                                  data/  (profile.yaml, jobs.db, documents/)
```

## Backend — FastAPI (`api/app.py`)

All routes bind to localhost; CORS is limited to local origins. Interactive
docs at `/docs` when the server is running. Full route inventory is in
[LLD.md § 8](LLD.md#8-api-route-inventory-apiapppy).

Highlights relevant to the web UI:

| Route | Used by |
|---|---|
| `GET/PUT /api/profile` | Profile editor (view + save) |
| `POST /api/profile/import-resume` | Profile edit — PDF import |
| `GET /api/jobs` | Jobs board |
| `POST /api/match` | AiMatch component (studio + jobs board) |
| `POST /api/resume/tailor` | Résumé studio live ATS scoring |
| `POST /api/resume/build` | Studio + jobs board download |
| `POST /api/resume/cover` | Jobs board cover-letter button |
| `GET/POST /api/applications` | Applications page CRUD |
| `GET /api/applications/stats` | Dashboard funnel counts |
| `GET/DELETE /api/documents` | Résumés page library |
| `GET /api/documents/{id}/file` | Download PDF |
| `GET/PUT /api/llm/config`, `POST /api/llm/test` | Settings page |
| `GET /api/sources`, `PUT /api/sources/config` | Settings page |
| `POST /api/sources/search` | Search page |
| `POST /api/sources/company` | Search page (company tab) |
| `GET /api/ops/status`, `POST /api/ops/*` | Jobs board scraper controls |
| `POST /api/chat` | Chat page |

## Frontend — Next.js 15 / React 19 / Tailwind

Lives in `web/` as a separate workspace. Uses App Router (no Pages Router).
The typed API client (`lib/api.ts`) is the single source of truth for the
request/response shapes — it mirrors the FastAPI models exactly; update it
whenever routes change.

### Page inventory

| Page | File | Purpose |
|---|---|---|
| Landing | `app/page.tsx` | Animated intro, self-typing terminal session replay, local-first pitch |
| Dashboard | `app/dashboard/page.tsx` | Funnel stats (applications by stage), recent jobs, quick-action cards |
| Job Search | `app/search/page.tsx` | Keyword + filter search across enabled sources; `SearchResultCard` per result; track result → new application |
| Applications | `app/applications/page.tsx` | `DataTable` with full CRUD; stage filter; link to generated résumé |
| Résumé Library | `app/resumes/page.tsx` | `DataTable` of `GeneratedDocument` records; download PDF; delete |
| Settings | `app/settings/page.tsx` | BYO-LLM provider config (chat + embed); job-source enable/disable + API keys; live test buttons |
| Profile (view) | `app/profile/page.tsx` | Read-only profile summary with résumé-style layout |
| Profile (edit) | `app/profile/edit/page.tsx` | Full section editor (education, experience, projects, skills, certs); résumé-PDF import |
| Jobs Board | `app/jobs/page.tsx` | Tracked portal postings; `JobsExplorer` with per-posting résumé/cover-letter buttons; scraper controls; session status |
| Résumé Studio | `app/studio/page.tsx` | Paste a JD → live ATS coverage + `AiMatch` → tailored PDF; `ResumePaper` preview |
| Chat | `app/chat/page.tsx` | Sentinel assistant (grounded on real data; local LLM for the rest) |
| Login | `app/login/page.tsx` | Auth gate shown when `AUTH_MODE=demo\|required` |

### Key components

| Component | File | Role |
|---|---|---|
| `Nav` | `components/Nav.tsx` | Top navigation bar |
| `CommandPalette` | `components/CommandPalette.tsx` | ⌘K / Ctrl+K overlay for fast navigation |
| `AiMatch` | `components/AiMatch.tsx` | Profile↔job match widget (score ring, verdict, strengths/gaps) |
| `DataTable` | `components/DataTable.tsx` | Reusable sortable/filterable table (used by Applications + Résumés pages) |
| `SearchResultCard` | `components/SearchResultCard.tsx` | Single job-source result card with "Track" action |
| `JobsExplorer` | `components/JobsExplorer.tsx` | Jobs board with scraper controls and per-posting document buttons |
| `ResumePaper` | `components/ResumePaper.tsx` | A4-style résumé preview panel |
| `ScraperControls` | `components/ScraperControls.tsx` | Session status, one-click scrape, watcher toggle |
| `JobActions` | `components/JobActions.tsx` | Per-posting action buttons (apply, tailor, cover) |
| `JobDocs` | `components/JobDocs.tsx` | Generated-document list for a posting |

### Typed API client (`lib/api.ts`)

`lib/api.ts` is the **single typed client** for all API routes. Keep it in
sync with `api/app.py`. It exports typed `fetch` wrappers plus TypeScript
interfaces for every request/response model. The demo shim (`lib/demo.ts`)
intercepts calls when `NEXT_PUBLIC_DEMO=1`.

### Demo mode (`lib/demo.ts`)

When `NEXT_PUBLIC_DEMO=1`, every API call in `lib/api.ts` is intercepted and
returns canned data from `lib/demo.ts` instead of hitting the local FastAPI
server. This powers the hosted demo on Vercel (`job-sentinel.vercel.app`) —
every screen is fully alive with realistic but fictional sample data. Nothing
in the demo is real personal data.

To build a demo-mode bundle:

```bash
cd web
NEXT_PUBLIC_DEMO=1 npm run build
```

### Standards

- Accessibility: WCAG AA baseline via semantic HTML + Tailwind `aria-*` props.
- Dark mode: Tailwind `dark:` variants throughout.
- Type-checking: `npm run typecheck` (`tsc --noEmit`).
- Tests: vitest (`npm test`).
- No ESLint config is committed (lint runs via Next.js built-in).

## Hosting

Runs fully locally now. The same API backs a future managed tier (see
[NORTH_STAR.md](../NORTH_STAR.md)) without changing the core. The hosted demo
(Vercel) runs in `NEXT_PUBLIC_DEMO=1` mode — no backend, no credentials,
purely client-side sample data.
