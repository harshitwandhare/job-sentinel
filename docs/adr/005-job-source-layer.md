# ADR-005: Pluggable Job-Source Layer

**Status:** Accepted | **Date:** 2026-06-13 | **Deciders:** Harshit Wandhare

---

## Context

Job Sentinel originally discovered jobs via Playwright scraping of gated portals
(12twenty, Handshake). Users asked for a complementary "browse the open web" mode
that:

1. Works without a portal session or a browser install.
2. Respects legal constraints — public APIs by default, scrapers opt-in.
3. Maps cleanly onto the existing `JobPosting` domain model.
4. Integrates with the existing application-tracking workflow.

---

## Decision

Add a `src/job_sentinel/sources/` package with:

- **`JobSource` ABC** — mirrors `SiteAdapter` but is HTTP-only (httpx, sync).
- **Default sources (no key, always on):** Remote OK, The Muse, Arbeitnow, Himalayas.
- **Opt-in sources (free user key required):** Adzuna, USAJobs.
- **Opt-in scraper (extra install):** JobSpy (`pip install job-sentinel[sources]`).
- **Company ATS boards:** Greenhouse, Lever, Ashby (public, zero auth).
- **Aggregate search** runs sources concurrently (ThreadPoolExecutor), isolates
  per-source failures, deduplicates results, sorts newest-first, caps to `limit`.
- Results are **ephemeral** — never written to the DB. Tracking is done via the
  existing `POST /api/applications` route.

---

## Legal posture

| Source class | Default | Rationale |
|---|---|---|
| Public APIs (RemoteOK, Arbeitnow, Himalayas, Muse) | **On** | Explicit public API, ToS-permissive |
| Key-required APIs (Adzuna, USAJobs) | Off | Free key; governs own ToS |
| JobSpy scraper | Off, opt-in extra | Scraping may violate target-site ToS |
| LinkedIn via JobSpy | **Never default** | Ref: *hiQ Labs v. LinkedIn Corp*; ongoing enforcement |
| Company ATS boards (Greenhouse/Lever/Ashby) | On-demand | Published public board APIs; no auth |

The `JobSpySource` class carries a `TOS_WARNING` docstring and raises a
helpful `RuntimeError` if the extra is not installed, so opt-in is intentional.

---

## Alternatives considered

| Option | Rejected because |
|---|---|
| Playwright scraping for all sources | Browser overhead, session management, fragile selectors |
| Apify cloud actors | External cloud dependency; added cost; violates zero-cost hosting goal |
| Single monolithic search function | Kills testability and source isolation |
| Always-on LinkedIn scraping | Legal risk; *hiQ* ruling applies to automated access too |

---

## Consequences

- New optional extras: `job-sentinel[sources]` (python-jobspy) and `job-sentinel[apify]`
  (reserved; apify-client).
- New settings group `JobSourceSettings` adds ~15 env vars (all secrets are `repr=False`).
- New API routes: `GET /api/sources`, `PUT /api/sources/config`,
  `POST /api/sources/search`, `POST /api/sources/company`.
- CLI parity: `job-sentinel sources list|search|company`.
- Web typed client (`web/lib/api.ts`) updated with `JobQuery`, `JobSourceStatus`,
  `SearchResponse`, and four functions.
- Coverage gate unchanged (≥ 70 %).
