"use client";

import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import type { ReactNode } from "react";

import type { Profile } from "@/lib/api";
import { externalUrl } from "@/lib/utils";

/**
 * Renders the profile exactly the way the LaTeX engine lays it out on paper:
 * a single-column, ATS-style sheet. The web view IS the résumé — what you see
 * here is what `resume build` prints.
 */
export function ResumePaper({ profile }: { profile: Profile }) {
  const { basics, education, experience, projects, skills, certifications, awards, publications } =
    profile;

  const contact = [basics.location, basics.email, basics.phone].filter(Boolean);

  return (
    <div className="w-full bg-white px-8 py-10 font-serif text-stone-900 sm:px-14 sm:py-14">
      {/* Header — centered, like the LaTeX template */}
      <header className="text-center">
        <h2 className="text-[26px] font-bold uppercase tracking-[0.08em] sm:text-[32px]">
          {basics.name || "Your Name"}
        </h2>
        {basics.headline && (
          <p className="mt-1 text-[13px] italic text-stone-600 sm:text-sm">{basics.headline}</p>
        )}
        {(contact.length > 0 || basics.links.length > 0) && (
          <p className="mx-auto mt-2 flex max-w-2xl flex-wrap items-center justify-center gap-x-2 gap-y-0.5 text-[12px] text-stone-700 sm:text-[13px]">
            {contact.map((c, i) => (
              <span key={c} className="inline-flex items-center gap-2">
                {i > 0 && <Dot />}
                {c}
              </span>
            ))}
            {basics.links.map((l) => (
              <span key={l.url} className="inline-flex items-center gap-2">
                {(contact.length > 0 || l !== basics.links[0]) && <Dot />}
                <a
                  href={externalUrl(l.url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline decoration-stone-300 underline-offset-2 hover:decoration-stone-700"
                >
                  {l.label || l.url}
                </a>
              </span>
            ))}
          </p>
        )}
      </header>

      {basics.summary && (
        <PaperSection title="Summary">
          <p className="text-[13px] leading-relaxed text-stone-800">{basics.summary}</p>
        </PaperSection>
      )}

      {education.length > 0 && (
        <PaperSection title="Education">
          {education.map((e, i) => (
            <Entry
              key={`${e.institution}-${i}`}
              left={e.institution}
              leftSub={[e.degree, e.gpa ? `GPA ${e.gpa}` : ""].filter(Boolean).join(" · ")}
              right={fmtRange(e.start, e.end)}
              rightSub={e.location}
              bullets={e.highlights}
            />
          ))}
        </PaperSection>
      )}

      {experience.length > 0 && (
        <PaperSection title="Experience">
          {experience.map((x, i) => (
            <Entry
              key={`${x.company}-${i}`}
              left={x.role}
              leftSub={x.company}
              right={fmtRange(x.start, x.end)}
              rightSub={x.location}
              bullets={x.bullets}
            />
          ))}
        </PaperSection>
      )}

      {projects.length > 0 && (
        <PaperSection title="Projects">
          {projects.map((p, i) => (
            <Entry
              key={`${p.name}-${i}`}
              left={p.name}
              leftSub={p.description}
              right={
                p.url ? (
                  <a
                    href={externalUrl(p.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-stone-300 underline-offset-2 hover:decoration-stone-700"
                  >
                    {shortUrl(p.url)}
                  </a>
                ) : undefined
              }
              bullets={p.bullets}
            />
          ))}
        </PaperSection>
      )}

      {skills.length > 0 && (
        <PaperSection title="Skills">
          <div className="space-y-0.5">
            {skills.map((g, i) => (
              <p key={`${g.category}-${i}`} className="text-[13px] leading-relaxed text-stone-800">
                <span className="font-bold">{g.category}:</span> {g.skills.join(", ")}
              </p>
            ))}
          </div>
        </PaperSection>
      )}

      {certifications.length > 0 && (
        <PaperSection title="Certifications">
          {certifications.map((c, i) => (
            <p key={`${c.name}-${i}`} className="text-[13px] leading-relaxed text-stone-800">
              <span className="font-bold">{c.name}</span>
              {[c.issuer, c.date].filter(Boolean).length > 0 &&
                ` — ${[c.issuer, c.date].filter(Boolean).join(", ")}`}
            </p>
          ))}
        </PaperSection>
      )}

      {awards.length > 0 && (
        <PaperSection title="Awards">
          {awards.map((a, i) => (
            <p key={`${a.title}-${i}`} className="text-[13px] leading-relaxed text-stone-800">
              <span className="font-bold">{a.title}</span>
              {[a.issuer, a.date].filter(Boolean).length > 0 &&
                ` — ${[a.issuer, a.date].filter(Boolean).join(", ")}`}
              {a.description && <span className="block text-stone-700">{a.description}</span>}
            </p>
          ))}
        </PaperSection>
      )}

      {publications.length > 0 && (
        <PaperSection title="Publications">
          {publications.map((p, i) => (
            <p key={`${p.title}-${i}`} className="text-[13px] leading-relaxed text-stone-800">
              <span className="font-bold">{p.title}</span>
              {[p.venue, p.date].filter(Boolean).length > 0 &&
                ` — ${[p.venue, p.date].filter(Boolean).join(", ")}`}
              {p.url && (
                <>
                  {" "}
                  <a
                    href={externalUrl(p.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-stone-300 underline-offset-2 hover:decoration-stone-700"
                  >
                    {shortUrl(p.url)}
                  </a>
                </>
              )}
            </p>
          ))}
        </PaperSection>
      )}
    </div>
  );
}

/**
 * The desk: a perspective stage that floats the sheet in 3D and tilts it
 * gently toward the pointer. Static under reduced motion or coarse pointers.
 */
export function PaperStage({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();
  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);
  const rotateX = useSpring(useTransform(py, [0, 1], [2.4, -2.4]), {
    stiffness: 140,
    damping: 22,
  });
  const rotateY = useSpring(useTransform(px, [0, 1], [-3, 3]), { stiffness: 140, damping: 22 });

  const sheet = (
    <div className="overflow-hidden rounded-[3px] shadow-paper ring-1 ring-black/10">{children}</div>
  );

  if (reduced) return <div className="mx-auto w-full max-w-[820px]">{sheet}</div>;

  return (
    <div
      className="mx-auto w-full max-w-[820px]"
      style={{ perspective: 1400 }}
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        px.set((e.clientX - r.left) / r.width);
        py.set((e.clientY - r.top) / r.height);
      }}
      onPointerLeave={() => {
        px.set(0.5);
        py.set(0.5);
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 28, rotateX: 6 }}
        animate={{ opacity: 1, y: 0, rotateX: 0 }}
        transition={{ duration: 0.7, ease: [0.21, 0.65, 0.36, 1] }}
        style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
      >
        {sheet}
      </motion.div>
    </div>
  );
}

function PaperSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6">
      <h3 className="border-b border-stone-300 pb-1 text-[12px] font-bold uppercase tracking-[0.18em] text-stone-900">
        {title}
      </h3>
      <div className="mt-2.5 space-y-3">{children}</div>
    </section>
  );
}

function Entry({
  left,
  leftSub,
  right,
  rightSub,
  bullets,
}: {
  left: string;
  leftSub?: string;
  right?: ReactNode;
  rightSub?: string;
  bullets?: string[];
}) {
  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <p className="text-[14px] font-bold text-stone-900">{left}</p>
        {right && <p className="text-[12px] text-stone-600">{right}</p>}
      </div>
      {(leftSub || rightSub) && (
        <div className="flex flex-wrap items-baseline justify-between gap-x-4">
          {leftSub ? (
            <p className="text-[13px] italic text-stone-700">{leftSub}</p>
          ) : (
            <span />
          )}
          {rightSub && <p className="text-[12px] italic text-stone-500">{rightSub}</p>}
        </div>
      )}
      {bullets && bullets.length > 0 && (
        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-[13px] leading-relaxed text-stone-800 marker:text-stone-400">
          {bullets.map((b, i) => (
            <li key={i}>{b}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Dot() {
  return (
    <span aria-hidden="true" className="text-stone-400">
      ·
    </span>
  );
}

function fmtRange(start: string, end: string): string {
  if (start && end) return `${start} – ${end}`;
  return start || end || "";
}

function shortUrl(url: string): string {
  return url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");
}
