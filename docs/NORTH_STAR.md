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

- **v0.1 — Foundation (DONE).** Adapter framework, 12twenty adapter, Telegram
  bot, SQLite persistence, typed config, CI, résumé engine (profile → ATS
  LaTeX/PDF), per-posting tailoring, optional local-LLM rephrasing.
- **v0.2 — Reliability & reach.** Persistent always-on (Docker + volume),
  backups, deadline-aware tracking + pre-deadline alerts, email notifier,
  supply-chain/license CI gates, `SECURITY.md`.
- **v0.3 — Smarter tailoring.** Local embeddings for semantic match, deeper
  ATS scoring (parser-style), cover-letter generation, JobSpy-style optional
  board adapters.
- **v0.4 — Surface.** A minimal **local** web/chat UI over the same engine.
  Packaging: PyPI releases, one-command install, docs site.
- **v1.0 — Platform.** Multi-profile, plugin API for community adapters/tailors,
  optional managed hosting tier (funds the project; core stays free & local).

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
| **Bun / JS toolchain** | ⏳ with the v0.4 UI | Adopt for the eventual web surface; the Python engine doesn't need it. |

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
