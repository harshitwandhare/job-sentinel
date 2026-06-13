# Compliance & data protection

Job Sentinel is built privacy-first, and its compliance posture follows directly
from that architecture. This page is the honest map of what applies and why.

## What kind of tool this is (and isn't)

Job Sentinel is a **candidate-side** assistant. It helps a job seeker:

- monitor portals and search public job sources,
- track their *own* applications,
- tailor their *own* résumé and cover letters.

It is **not** an Automated Employment Decision Tool (AEDT). It does not screen,
score, rank, or filter other candidates on an employer's behalf, and it makes no
hiring decisions about anyone.

That distinction matters legally:

- **NYC Local Law 144** (AEDT bias audits) targets *employers and employment
  agencies* using AI to screen candidates. It does not apply to a job seeker's
  personal assistant. ([overview](https://www.warden-ai.com/resources/hr-tech-compliance-nyc-local-law-144))
- **EU AI Act** classifies *recruitment/candidate-evaluation systems used by
  employers* as high-risk. A candidate-side tool that organizes your own search
  is not in that high-risk category. The Act's general **transparency** duty —
  tell users when they're interacting with AI and when content is AI-generated —
  is the part we honor. ([context](https://www.candidate-experience-institute.com/your-new-hiring-ai-compliance-stack-what-eu-ai-act-and-nyc-local-law-144-actually-require-of-your-ats-roadmap))

## Data protection (GDPR / CCPA principles)

These apply to personal data regardless of tool category, and the local-first
design satisfies them by construction:

| Principle | How Job Sentinel meets it |
|---|---|
| **Data minimization** | Only what you enter (profile) or fetch (public postings) is stored. |
| **Storage limitation** | Everything lives in local files/SQLite you control; nothing is retained on our servers because there are none. |
| **Right to erasure** | Every entity (profile, applications, generated documents, jobs) has a delete path in CLI, API, and UI. Personal data is never baked into model weights (see [ADR 006](adr/006-ai-personalization-and-data-strategy.md)), so it stays deletable. |
| **Purpose limitation / no secondary use** | No telemetry, no analytics, no third-party sharing. Data leaves the machine only if *you* configure a BYO cloud LLM, and then only the prompt you chose to send. |
| **Security** | Secrets live in a local `.env` (gitignored), are never logged (pydantic `repr=False` + redaction), and API responses never echo raw keys or exception/stack detail. |
| **Transparency** | Generated documents record which model/provider produced them and whether AI rephrasing was used; the UI labels AI output. |

## Ethical guardrails (self-imposed)

- **No fabrication.** The tailoring contract forbids inventing employers, titles,
  dates, metrics, or skills; output is validated and falls back to your own words.
- **No auto-submit, no CAPTCHA-defeating, no detection evasion.** Human-in-the-loop
  for every application.
- **Scrapers are opt-in and ToS-disclaimed.** Legal/free APIs are the default;
  scraping backends (JobSpy/Apify) are off by default and clearly flagged.

## Third-party data sources

When you enable an external source, its terms apply to your use:

- Default API sources (RemoteOK, The Muse, Arbeitnow, Himalayas, Adzuna, USAJobs)
  are used via their official APIs with attribution where required.
- Scraper backends (JobSpy, Apify) may violate the target site's Terms of
  Service; they are opt-in and you assume responsibility for that use.

## License

The project is MIT-licensed. Third-party dependency licenses are inventoried by
`scripts/check_licenses.py` (strong-copyleft GPL/AGPL is blocked in CI).
