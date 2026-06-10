# Job Sentinel — Web UI

A local-first web surface over the Job Sentinel engine, built with **Next.js 15
(App Router) + TypeScript + Tailwind + framer-motion**. It talks to the local
FastAPI backend — there's no business logic here, only views.

## Run it

```bash
# One command from the repo root
job-sentinel web              # API + http://localhost:3000

# Or run the two processes manually
job-sentinel serve            # http://127.0.0.1:8000
cd web
cp .env.example .env.local    # points at the API
npm install
npm run dev                   # http://localhost:3000
```

## Pages
- `/` — landing (animated intro, the local-first pitch).
- `/profile` — your universal profile, rendered from `GET /api/profile`.
- `/jobs` — tracked postings from `GET /api/jobs`, with status + deadlines.

Every API call degrades gracefully to an empty state if the backend is down, so
the UI never hard-crashes.

## Roadmap
- Profile **editor** (write back via `PUT /api/profile`).
- **Résumé studio**: pick a posting → tailor (toggle local LLM) → preview/download PDF.
- A `three.js` / react-three-fiber hero on the landing page.
- Its own lint + build CI job.
