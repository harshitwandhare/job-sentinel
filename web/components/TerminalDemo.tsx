"use client";

import { useEffect, useRef, useState } from "react";

/**
 * A self-typing terminal that replays a real Job Sentinel session — actual
 * commands, actual output shapes. Pure CSS/JS (no deps), respects
 * prefers-reduced-motion by rendering the finished transcript instead.
 */

interface Line {
  text: string;
  kind: "cmd" | "out" | "ok" | "dim";
  /** ms pause after the line completes */
  pause?: number;
}

const SCRIPT: Line[] = [
  { text: "$ job-sentinel session", kind: "cmd" },
  { text: "✓ Session valid as Harshit Wandhare", kind: "ok", pause: 500 },
  { text: "$ job-sentinel scrape", kind: "cmd" },
  { text: "▶ adapter=12twenty · capturing portal API…", kind: "dim" },
  { text: "✓ 16 postings · enriched with salary, contacts, deadlines", kind: "ok", pause: 500 },
  { text: "$ job-sentinel resume build --ai \\", kind: "cmd" },
  { text: "    --job-text \"Museum Visitor Services…\"", kind: "cmd" },
  { text: "ATS keyword coverage: 87%", kind: "out" },
  { text: "✓ Resume built → data/resume.pdf", kind: "ok", pause: 1800 },
];

const COLORS: Record<Line["kind"], string> = {
  cmd: "text-stone-100",
  out: "text-stone-300",
  ok: "text-emerald-400",
  dim: "text-stone-500",
};

const TYPE_MS = 28; // per character on command lines
const OUT_MS = 220; // whole-line delay for output lines

export function TerminalDemo() {
  const [lines, setLines] = useState<{ text: string; kind: Line["kind"] }[]>([]);
  const [reduced, setReduced] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) {
      setReduced(true);
      setLines(SCRIPT.map(({ text, kind }) => ({ text, kind })));
      return;
    }

    let lineIdx = 0;
    let charIdx = 0;
    let cancelled = false;

    const tick = () => {
      if (cancelled) return;
      if (lineIdx >= SCRIPT.length) {
        // loop: clear and restart after a beat
        timer.current = setTimeout(() => {
          if (cancelled) return;
          setLines([]);
          lineIdx = 0;
          charIdx = 0;
          tick();
        }, 2500);
        return;
      }
      const line = SCRIPT[lineIdx];
      if (line.kind === "cmd") {
        charIdx += 1;
        setLines((prev) => {
          const next = prev.slice(0, lineIdx);
          next[lineIdx] = { text: line.text.slice(0, charIdx), kind: line.kind };
          return next;
        });
        if (charIdx < line.text.length) {
          timer.current = setTimeout(tick, TYPE_MS);
        } else {
          lineIdx += 1;
          charIdx = 0;
          timer.current = setTimeout(tick, line.pause ?? 150);
        }
      } else {
        setLines((prev) => [...prev.slice(0, lineIdx), { text: line.text, kind: line.kind }]);
        lineIdx += 1;
        timer.current = setTimeout(tick, line.pause ?? OUT_MS);
      }
    };

    timer.current = setTimeout(tick, 800);
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  return (
    <div
      aria-hidden="true"
      className="select-none rounded-2xl border border-white/10 bg-black/45 shadow-2xl shadow-black/40 backdrop-blur-md"
    >
      <div className="flex items-center gap-1.5 border-b border-white/10 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-rose-500/80" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
        <span className="ml-3 font-mono text-[11px] text-stone-500">harshit@sentinel — pwsh</span>
      </div>
      <div className="h-[260px] overflow-hidden px-4 py-3 font-mono text-[12.5px] leading-6">
        {lines.map((l, i) => (
          <div key={i} className={COLORS[l.kind]}>
            {l.text}
            {!reduced && i === lines.length - 1 && (
              <span className="ml-0.5 inline-block h-3.5 w-[7px] animate-pulse bg-emerald-400 align-middle" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
