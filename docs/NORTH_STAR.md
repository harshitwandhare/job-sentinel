# North Star — vision, scope, and the path to scale

**Status:** living document · **Owner:** Harshit Wandhare

Job Sentinel starts as a personal, local, on-campus job monitor + résumé engine.
The ambition is larger: the best **local-first, open-source** career-automation
platform of the 2026–2028 era — private by default, integrated end-to-end, and
engineered to a standard a FAANG reviewer respects on sight.

This document is the durable plan. It exists so every decision can be checked
against a thesis, and so we never build infrastructure before it earns its keep.

---

## 1. Principles

1. **Local-first, private by default.** Your career data and the models that
   touch it stay on your machine. Cloud is opt-in, never required.
2. **Right-size, ruthlessly.** Add infrastructure only when a real constraint
   demands it. Premature Kafka/Redis/Kubernetes in a single-user app is
   anti-quality, not pro-quality. (See §4.)
3. **Pluggable seams, graceful degradation.** Adapters, notifiers, tailors,
   models — all behind small interfaces; the product works when the heavy/
   optional piece is absent.
4. **Quality is the moat.** Typed, tested, CI-gated, documented. Boring,
   correct, legible code beats clever code.
5. **Ethical & ToS-respecting.** No auto-submit, no CAPTCHA-defeating, no
   detection-evasion. Human-in-the-loop where it matters.
6. **Token- and context-aware.** The agentic workflow that builds this (see §5)
   is itself optimized: small, verifiable steps; reuse over regeneration.

## 2. Domains (the product, eventually)

```
            ┌──────────────────────────── Job Sentinel ────────────────────────────┐
 discovery →│  adapters (portals + boards) → DB (lifecycle) → notifiers (TG/email)  │
            │                                   │                                    │
   profile →│  universal profile (YAML) → tailor (keyword | local-LLM) → LaTeX/PDF   │
            │                                   │                                    │
            │              deadline-aware tracking · per-posting documents           │
            └────────────────────────────────────────────────────────────────────────┘
                         CLI today · thin local UI later · managed hosting much later
```

## 3. Roadmap (sequenced, each phase shippable)

### Shipped

- **v0.1 — Foundation (DONE).** Adapter framework, 12twenty adapter, Telegram
  bot, SQLite persistence, typed config, CI, résumé engine (profile → ATS
  LaTeX/PDF), per-posting tailoring, optional local-LLM rephrasing.
- **v0.2 — Reliability & reach (DONE).** Persistent always-on (Docker + volume),
  deadline-aware tracking + pre-deadline alerts, email notifier,
  supply-chain/license CI gates, `SECURITY.md`.
- **v0.3 — Smarter tailoring (DONE).** Local embeddings for semantic match,
  cover-letter generation, PyPI releases.
- **v0.4 — Surface (DONE).** Local Next.js web UI over the engine (landing,
  profile-as-résumé, jobs, studio, chat), docs site, hosted demo.
- **v0.9 — Platform breadth (DONE, 2026-06).** The leap from "portal scanner" to
  full career platform:
  - **BYO LLM providers** — OpenAI-compatible chat + embeddings (OpenAI/
    OpenRouter/Groq/Gemini) alongside Ollama; zero-config local default. (ADR-ish
    in `docs/llm-providers.md`.)
  - **Application tracker + document library** — `applications` and
    `generated_documents` data model, full CRUD, pipeline UI, résumé library.
  - **Pluggable job sources** — legal/free APIs by default (RemoteOK, The Muse,
    Arbeitnow, Himalayas), Adzuna/USAJobs free-key opt-ins, JobSpy/Apify opt-in
    scraper tier, follow-companies via Greenhouse/Lever/Ashby ([ADR 005](adr/005-job-source-layer.md)).
  - **LinkedIn-style search UI** with full filter set + one-click tracking.

### Next

- **v1.0 — Intelligence & polish.** RAG over the user's own corpus (profile +
  generated docs + applications) powering an **AI profile↔job match score** with
  rationale and a grounded assistant ([ADR 006](adr/006-ai-personalization-and-data-strategy.md));
  a real **dashboard** (funnel, deadlines, match insights, source health);
  deeper parser-style ATS scoring; seeded demo so every screen is alive on the
  hosted demo; a full security + compliance pass ([compliance](compliance.md)).
- **v1.x — Distribution & community.** One-command installer, browser extension
  (clip-to-track, no auto-submit), Discord notifier, Playwright e2e, more source
  adapters, a documented plugin API so the community can add adapters/sources/
  tailors.
- **v2.0 — The thesis at scale (next North Star).** Multi-profile; an optional
  **managed-hosting tier** that funds the project without closing the core
  (self-host stays free + local forever); ghost-job and reposting signals;
  application analytics (response-rate by source/role/time); visa-sponsorship
  detection. The durable bet: as AI commoditizes résumé generation, the moat is
  **privacy + integration + transparent, owned career data** — the one career
  tool a user trusts because it runs on their machine and they can read every
  byte.

## 4. Infrastructure decisions (and explicit non-decisions)

A senior reviewer judges what you *didn't* add as much as what you did.

| Tech | Decision | Rationale |
|---|---|---|
| **SQLite** | ✅ now | Single-user, zero-ops, file-backed durability, WAL concurrency. Correct for this scale. |
| **Docker + named volume** | ✅ v0.2 | Always-on + restart-safe data without a server. Right-sized ops. |
| **Postgres** | ⏳ when multi-user | Only when concurrent writers / a hosted tier exist. Migration path noted in the repository layer. |
| **Redis** | ⏳ when there's shared cross-process state / rate-limit coordination | Today APScheduler + SQLite suffice. No cache to justify it. |
| **Kafka / queues** | ⏳ when fan-out across services exists | A single poll loop is not a streaming workload. Adding it now is cosplay, not architecture. |
| **Kubernetes** | ❌ until a real fleet exists | One always-on process belongs in `docker compose`/systemd, not k8s. |
| **Vector store** | ✅ SQLite (for v1.0 RAG) | Personal corpus is small; embed into SQLite (`sqlite-vec`) or in-memory cosine. A hosted/served vector DB is unjustified at single-user scale. [ADR 006](adr/006-ai-personalization-and-data-strategy.md) |
| **Fine-tuning on personal data** | ❌ use RAG instead | Baking personal data into weights breaks deletability/freshness/privacy. RAG grounds answers and stays deletable. Optional future LoRA for *writing style only*, never facts. [ADR 006](adr/006-ai-personalization-and-data-strategy.md) |
| **Knowledge graph / graph DB** | ❌ | `profile.yaml` + derived SQLite relations give explainable matching without Neo4j ops. |
| **Bun / JS toolchain** | ⏳ with the web UI | The Python engine doesn't need it. |

The point isn't "never" — it's "not before the constraint is real," and the
seams (repository layer, notifier/tailor interfaces) are designed so each can be
introduced without a rewrite.

## 5. The agent harness (how this gets built)

This repo is built by an AI agent working for, and fully controlled by, the
owner. That workflow is itself an engineered system:

- **Ownership & control.** All authorship is the owner's; agents never appear as
  authors/committers (see `.github/CODEOWNERS`, `AGENTS.md`). The human approves
  outward/irreversible actions.
- **Persistent memory.** Durable facts/decisions live in the agent memory store
  so context survives across sessions instead of being re-derived (token cost).
- **Token/context discipline.** Prefer small, independently-verifiable changes;
  reuse existing code/tests; avoid regenerating what already exists; lean on the
  gates (ruff/mypy/pytest/CI) as the correctness oracle rather than re-reading
  everything.
- **Skills/playbooks.** Repeatable procedures (add an adapter, add a notifier,
  cut a release) are documented so they're cheap to re-run.

## 6. Definition of "best open-source option"

A newcomer should, within minutes, see: green CI with real gates, typed code,
honest docs (HLD/LLD/ADRs/this), a local-first privacy story, and a clean,
extensible architecture — and conclude this is maintained to a professional bar.
That perception is a feature; we invest in it deliberately.
