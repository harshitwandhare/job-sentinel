"use client";

import { useEffect, useState } from "react";

/**
 * A self-typing terminal that replays a real Job Sentinel session — actual
 * commands, actual output shapes. Pure CSS/JS (no deps), respects
 * prefers-reduced-motion by rendering the finished transcript instead.
 *
 * The visible text is derived purely from a (line, char) progress counter,
 * so no frame can ever show partially-interleaved/garbled output.
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

interface Progress {
  line: number; // index into SCRIPT of the line being revealed
  chars: number; // characters of that line currently shown (cmd lines only)
}

const DONE: Progress = { line: SCRIPT.length, chars: 0 };

export function TerminalDemo() {
  const [progress, setProgress] = useState<Progress>({ line: 0, chars: 0 });
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setReduced(true);
      setProgress(DONE);
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const step = (p: Progress) => {
      if (cancelled) return;
      setProgress(p);

      if (p.line >= SCRIPT.length) {
        timer = setTimeout(() => step({ line: 0, chars: 0 }), 2500); // loop
        return;
      }
      const current = SCRIPT[p.line];
      const isTypingCmd = current.kind === "cmd" && p.chars < current.text.length;
      if (isTypingCmd) {
        timer = setTimeout(() => step({ line: p.line, chars: p.chars + 1 }), TYPE_MS);
      } else {
        const delay = current.pause ?? (current.kind === "cmd" ? 150 : OUT_MS);
        timer = setTimeout(() => step({ line: p.line + 1, chars: 0 }), delay);
      }
    };

    timer = setTimeout(() => step({ line: 0, chars: 0 }), 800);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  // Pure derivation: everything before `progress.line` is fully shown; the
  // current line is sliced to `progress.chars` if it's a typed command.
  const visible = SCRIPT.slice(0, Math.min(progress.line + 1, SCRIPT.length)).map((line, i) => {
    const isCurrent = i === progress.line;
    const text =
      isCurrent && line.kind === "cmd" ? line.text.slice(0, progress.chars) : line.text;
    return { text, kind: line.kind };
  });

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
        {visible.map((l, i) => (
          <div key={i} className={COLORS[l.kind]}>
            {l.text}
            {!reduced && i === visible.length - 1 && (
              <span className="ml-0.5 inline-block h-3.5 w-[7px] animate-pulse bg-emerald-400 align-middle" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
