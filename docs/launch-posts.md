# Launch posts (drafts)

Internal copy for launching Job Sentinel. Tweak the voice to your own before
posting — these are starting points, written to be honest and non-salesy
(HN and r/cscareerquestions both punish marketing fluff).

Links to fill in: live demo `https://job-sentinel.vercel.app`, repo
`https://github.com/harshitwandhare/job-sentinel`.

---

## Show HN

**Title** (≤ 80 chars, no emoji, "Show HN:" prefix):

> Show HN: Job Sentinel – local-first, open-source job search + AI résumé tailoring

**Body:**

> I'm a CS student and the 2026 new-grad search broke me a little: the average
> opening gets ~242 applications, a third of listings are ghost jobs, and most
> résumés are rejected by an AI before a human sees them. Every tool that helps
> (Simplify, Teal, Huntr, Jobscan) is cloud SaaS that holds your résumé and
> application history behind a freemium meter.
>
> So I built the opposite: Job Sentinel runs entirely on your machine.
>
> - **Search jobs across sources** (RemoteOK, The Muse, Arbeitnow, Himalayas
>   out of the box, no keys; Adzuna/USAJobs with a free key; company ATS boards
>   via Greenhouse/Lever/Ashby). Scrapers (JobSpy) are strictly opt-in.
> - **Track applications** + a **clip-to-track browser extension** (one click on
>   any posting → your tracker). Tracking only — it never auto-submits.
> - **AI profile↔job match** and **ATS-tuned résumé/cover-letter generation**
>   (real LaTeX → PDF). The model is local via Ollama by default, or bring your
>   own key (OpenAI/OpenRouter/Groq/Gemini). Personalization is RAG over your own
>   data — nothing is fine-tuned into weights, so your data stays deletable and
>   never leaves the box.
>
> Stack: Python (FastAPI + Typer + Playwright + SQLite) and a Next.js UI; typed
> end to end (mypy --strict), ~450 tests, CodeQL/secret/license CI gates. MIT.
>
> Live demo (bundled sample data, zero backend): <demo link>
> Repo + 5-minute setup: <repo link>
>
> It deliberately doesn't auto-apply or defeat CAPTCHAs — I'd rather not get
> people's accounts banned. Honest limitations: PDF builds need a local LaTeX
> engine (Tectonic), and broad-board coverage depends on which sources you
> enable. Would love feedback on the source abstraction and the match scoring.

**Posting tips:** post Tue–Thu ~8–10am ET; reply to every early comment; lead
with the "why local-first" in replies, not features.

---

## r/cscareerquestions (or r/csMajors)

**Title:**

> I built a free, open-source, local-first job tracker + AI résumé tailor because the paid ones felt gross

**Body:**

> Like everyone here, I'm drowning in the new-grad search — hundreds of apps,
> ghost jobs, ATS black holes. The tools that help are all subscriptions that
> store your whole job history and résumé on their servers.
>
> I made an open-source one that runs on your own laptop:
>
> - aggregates jobs from free sources + your university portal, all in one place
> - tracks every application (saved → applied → interview → offer) with a
>   one-click browser extension to clip postings from LinkedIn/Greenhouse/etc.
> - scores how well your profile matches a posting and generates an ATS-clean,
>   tailored résumé + cover letter (LaTeX PDF)
> - uses a local AI model (free) or your own API key — your data never leaves
>   your machine, and nothing is sold or tracked
>
> It's free and MIT-licensed. No auto-apply (I didn't want to risk anyone's
> accounts). There's a live demo you can click around without installing
> anything: <demo link>. Repo: <repo link>.
>
> I'd genuinely love feedback from people deep in the grind — what would
> actually save you time? (Also happy to answer how the ATS scoring works.)

**Note:** check the subreddit's self-promotion rules first; frame as "I built
this to solve my own problem, feedback wanted," engage in comments, don't drop
and run.

---

## r/Python / r/opensource (technical angle, optional)

**Title:**

> Job Sentinel: a local-first job-search + résumé platform (FastAPI + Next.js, BYO-LLM or Ollama)

**Body:**

> Open-source (MIT) job-search platform that runs entirely locally. Python core
> (FastAPI, Typer, Playwright, SQLite via sqlite-utils) + Next.js UI. Things
> that might interest this crowd:
>
> - **Pluggable job sources** behind one interface — public APIs by default,
>   scrapers opt-in; ~50 lines to add a new one.
> - **Multi-provider LLM layer** over a single OpenAI-compatible path (Ollama,
>   OpenAI, OpenRouter, Groq, Gemini) with graceful deterministic fallback.
> - **RAG over your own profile/docs** for match + tailoring — no fine-tuning,
>   so personal data stays deletable (write-up in ADR 006).
> - Typed end-to-end (mypy --strict), ~450 tests, CodeQL + pip-audit + license
>   gates, ADRs/HLD/LLD.
>
> Repo: <repo link> · Demo: <demo link>. Feedback on the architecture welcome.
