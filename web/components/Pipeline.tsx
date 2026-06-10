"use client";

import { motion, useReducedMotion } from "framer-motion";

const steps = [
  { n: "01", title: "Monitor", body: "Pluggable Playwright adapters watch your portals on a schedule — even Cloudflare-gated ones, via one-time session capture." },
  { n: "02", title: "Track", body: "Every posting's lifecycle in SQLite: new → seen → applied → closed, with parsed deadlines and instant Telegram + email alerts." },
  { n: "03", title: "Tailor", body: "Keyword + semantic-embedding ranking reorder your profile per posting; a local LLM rephrases bullets with no-fabrication guards." },
  { n: "04", title: "Apply", body: "One click renders an ATS-clean LaTeX résumé and cover letter as PDF — you stay in control of the final submit." },
];

export function Pipeline() {
  const reduced = useReducedMotion();
  return (
    <div className="relative">
      {/* The connecting path, drawn as you scroll into it. */}
      <svg
        aria-hidden="true"
        viewBox="0 0 1000 8"
        preserveAspectRatio="none"
        className="absolute left-[12.5%] right-[12.5%] top-7 hidden h-2 w-3/4 lg:block"
      >
        <motion.path
          d="M 0 4 H 1000"
          fill="none"
          stroke="var(--brand)"
          strokeWidth="2"
          strokeDasharray="6 8"
          initial={reduced ? { pathLength: 1 } : { pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 1.4, ease: "easeInOut" }}
        />
      </svg>

      <ol className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s, i) => (
          <motion.li
            key={s.n}
            initial={reduced ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: i * 0.12 }}
            className="relative"
          >
            <div className="relative z-10 grid h-14 w-14 place-items-center rounded-2xl border border-line bg-surface font-mono text-sm font-bold text-brand shadow-card">
              {s.n}
            </div>
            <h3 className="mt-4 text-lg font-semibold tracking-tight text-ink">{s.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{s.body}</p>
          </motion.li>
        ))}
      </ol>
    </div>
  );
}
