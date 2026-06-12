"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  BookOpen,
  Briefcase,
  FileText,
  Github,
  Home,
  LogIn,
  MessageSquare,
  Package,
  Wand2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/** Dispatch this event from anywhere (e.g. the nav button) to open the palette. */
export const OPEN_EVENT = "sentinel:command-palette";

interface Item {
  label: string;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  external?: boolean;
  keywords?: string;
}

const ITEMS: Item[] = [
  { label: "Home", hint: "Landing page", icon: Home, href: "/" },
  { label: "Chat", hint: "Ask Sentinel about your jobs", icon: MessageSquare, href: "/chat" },
  { label: "Profile", hint: "Your résumé, rendered live", icon: FileText, href: "/profile" },
  { label: "Studio", hint: "Tailor + score against a job description", icon: Wand2, href: "/studio" },
  { label: "Jobs", hint: "Tracked postings & deadlines", icon: Briefcase, href: "/jobs", keywords: "deadlines tracked postings" },
  { label: "Sign in", hint: "Account / demo access", icon: LogIn, href: "/login", keywords: "login account" },
  {
    label: "GitHub",
    hint: "Star the repo — it keeps the project alive",
    icon: Github,
    href: "https://github.com/harshitwandhare/job-sentinel",
    external: true,
    keywords: "source star repository",
  },
  {
    label: "Docs",
    hint: "Setup, adapters, architecture",
    icon: BookOpen,
    href: "https://harshitwandhare.github.io/job-sentinel/",
    external: true,
    keywords: "documentation guide help",
  },
  {
    label: "PyPI",
    hint: "pip install job-sentinel",
    icon: Package,
    href: "https://pypi.org/project/job-sentinel/",
    external: true,
    keywords: "install pip package",
  },
];

/**
 * A keyboard-first launcher: ⌘K / Ctrl+K anywhere, type to filter, Enter to
 * go. Closes on Escape, backdrop click, or navigation.
 */
export function CommandPalette() {
  const router = useRouter();
  const reduced = useReducedMotion();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_EVENT, onOpen);
    };
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      // Focus after the enter animation has mounted the input.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return ITEMS;
    return ITEMS.filter((it) =>
      `${it.label} ${it.hint} ${it.keywords ?? ""}`.toLowerCase().includes(q),
    );
  }, [query]);

  function go(item: Item) {
    setOpen(false);
    if (item.external) window.open(item.href, "_blank", "noopener,noreferrer");
    else router.push(item.href);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      e.preventDefault();
      go(results[active]);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={reduced ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={reduced ? undefined : { opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-[90] flex items-start justify-center bg-night/40 px-4 pt-[16vh] backdrop-blur-sm"
          onMouseDown={() => setOpen(false)}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            initial={reduced ? false : { opacity: 0, scale: 0.97, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={reduced ? undefined : { opacity: 0, scale: 0.97, y: -8 }}
            transition={{ duration: 0.18, ease: [0.21, 0.65, 0.36, 1] }}
            className="w-full max-w-lg overflow-hidden rounded-2xl border border-line bg-surface shadow-lift"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-line px-4">
              <span aria-hidden="true" className="font-mono text-sm text-brand">
                ◈
              </span>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActive(0);
                }}
                onKeyDown={onKeyDown}
                placeholder="Where to?"
                aria-label="Search pages and actions"
                className="h-12 w-full bg-transparent text-sm text-ink outline-none placeholder:text-muted/70"
              />
              <kbd className="rounded border border-line bg-bg px-1.5 py-0.5 font-mono text-[10px] text-muted">
                esc
              </kbd>
            </div>
            <ul className="max-h-72 overflow-y-auto p-2" role="listbox" aria-label="Results">
              {results.length === 0 && (
                <li className="px-3 py-6 text-center text-sm text-muted">No matches.</li>
              )}
              {results.map((it, i) => (
                <li key={it.href} role="option" aria-selected={i === active}>
                  <button
                    onClick={() => go(it)}
                    onMouseEnter={() => setActive(i)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                      i === active ? "bg-brand/10 text-ink" : "text-muted",
                    )}
                  >
                    <it.icon className={cn("h-4 w-4 shrink-0", i === active ? "text-brand" : "")} />
                    <span className="font-medium text-ink">{it.label}</span>
                    <span className="min-w-0 flex-1 truncate text-xs text-muted">{it.hint}</span>
                    {it.external && (
                      <span aria-hidden="true" className="text-xs text-muted/70">
                        ↗
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex items-center gap-3 border-t border-line bg-bg px-4 py-2 text-[11px] text-muted">
              <span>
                <kbd className="font-mono">↑↓</kbd> navigate
              </span>
              <span>
                <kbd className="font-mono">↵</kbd> open
              </span>
              <span className="ml-auto">Job Sentinel</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
