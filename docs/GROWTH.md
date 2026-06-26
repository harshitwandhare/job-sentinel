# Growth & competitive strategy

**Status:** living playbook · **Owner:** Harshit Wandhare

The goal for the next 1–2 years is singular: **be the best job-search tool in the
world, open-source and local-first.** Not revenue — *users and reputation*.
Monetization (an optional managed tier that keeps the core free + local) comes
later, once there's a real user base. Until then every decision optimizes for
"is this the best, most trustworthy, most useful version for the job seeker?"

This page is the **repeatable loop** for staying ahead. Run it continuously.

---

## The loop: Scan → Triage → Decide → Ship → Measure

1. **Scan** the market on a cadence (sources below). Capture anything new:
   competitor features/changelogs, launches, research, pain points, complaints.
2. **Triage** each finding into one of: *copy-and-beat*, *ignore (off-thesis)*,
   *watch*, or *already-better*. Record it (see "Recording findings").
3. **Decide** with the moat filter (below) — only build what deepens our edge.
4. **Ship** it the usual way: branch → PR → green CI → merge → release.
5. **Measure** — GitHub stars/issues, demo traffic, HN/Reddit reception, and
   honest "are we still the best at X?" checks. Feed back into the next scan.

**Cadence:** market scan every ~2 weeks (or before each release); security scan
every 3 days (automated, `.github/workflows/security-scan.yml`); ship as ready.

---

## Where to scan

- **Hacker News** — "Show HN" launches, and AI/job-search/résumé threads.
- **Reddit** — r/cscareerquestions, r/csMajors, r/jobs, r/jobsearch,
  r/resumes, r/opensource, r/selfhosted (pain points + competitor mentions).
- **Product Hunt** — new job-search / résumé / AI-career launches.
- **GitHub** — Trending (job-search, ats, resume topics) + watch competitor
  repos and their releases/changelogs.
- **Competitor blogs/changelogs** — Simplify, Teal, Huntr, Jobscan, Careerflow,
  Rezi, plus LinkedIn/Indeed product changes.
- **Research** — arXiv / papers on RAG, résumé–JD matching, ATS parsing,
  retrieval, on-device LLMs, recruiting bias/regulation.
- **Market reports** — periodic job-market / hiring-AI statistics (refresh the
  numbers we cite in the README/landing).

## Competitor watchlist

| Who | What they're best at | Where we beat them |
|---|---|---|
| Simplify | Autofill across ATS (1M+ users) | Local-first, private; we don't ship your data to a cloud; clip-to-track without account |
| Teal / Huntr | Polished tracker + résumé tailoring (paid) | Free + unlimited via local LLM; data sovereignty; one integrated loop |
| Jobscan | ATS keyword match-rate | Semantic (not just keyword) match; transparent rationale; free |
| Rezi / Careerflow | AI résumé builders | LaTeX-grade PDFs; no fabrication; runs offline |
| JobSync / OSS trackers | Self-hostable | Deeper: search + match + tailor + extension, typed/tested/CI'd to a pro bar |

## The moat filter (what to build)

Build it **only if it deepens at least one durable moat**:
1. **Privacy / local-first** — data stays on the user's machine.
2. **Integration** — the whole loop (watch → search → match → tailor → track),
   not a point tool.
3. **Transparency** — explainable scores, no black boxes, no fabrication.
4. **Engineering quality** — typed, tested, CI-gated; a fork gains little.
5. **Cost** — free and unlimited where rivals meter.

Reject features that break local-first, add tracking, enable ToS-violating
auto-submit, or are pure parity with no moat angle.

## Opportunity backlog (researched, prioritized)

Turn these into GitHub issues as they're picked up:

- **Deeper ATS scoring** — parser-style simulation of the big enterprise ATSes,
  beyond keyword coverage (learn from open ATS-screener projects).
- **Ghost-job / repost signals** — flag stale or recycled listings before the
  user sinks hours in (a top 2026 pain point). *(client-side heuristics shipped in v1.1.0)*
- **Application analytics** — response-rate by source/role/time over the user's
  own history (no SaaS competitor does this on private data). *(shipped v1.1.0: funnel +
  response-rate endpoint; dashboard panel wired June 2026)*
- **Browser-extension autofill assist** — prefill/copy helpers (never
  auto-submit) to match Simplify's convenience without the ban risk.
- **Local email/Gmail status parsing** — detect "applied/interview/reject"
  updates from the inbox, on-device.
- **Interview prep** — local-LLM mock questions from the JD + your profile.
- **More sources & notifiers** — additional legal APIs; Discord webhook.
- **Visa-sponsorship detection** — LLM-label postings (big for intl. students). *(shipped v1.1.0)*
- **Mobile/PWA polish** and broader accessibility.
- **ATS deadline urgency in the tracker** — deadline countdown column in
  the Applications table so users know when a tracked role closes. *(shipped June 2026)*

## Recording findings

- Drop each scan's notes in `docs/research/` (date-stamped) and refresh
  `docs/research/competitive-analysis.md` when the landscape shifts.
- File concrete opportunities as GitHub issues with the moat angle stated.
- Keep the README/landing market stats current (they're a credibility signal).
