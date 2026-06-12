"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const links = [
  { href: "/chat", label: "Chat" },
  { href: "/profile", label: "Profile" },
  { href: "/studio", label: "Studio" },
  { href: "/jobs", label: "Jobs" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-line/80 bg-bg/80 backdrop-blur-md">
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3"
      >
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight text-ink">
          <img
            src="/brand/sentinel.png"
            alt=""
            className="h-8 w-8 rounded-lg border border-white/10 bg-night object-cover shadow-sm"
            aria-hidden="true"
          />
          Job Sentinel
        </Link>
        <ul className="hidden items-center gap-6 text-sm text-muted sm:flex">
          {links.map((l) => {
            const active = pathname === l.href || pathname.startsWith(`${l.href}/`);
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "transition-colors hover:text-ink",
                    active && "font-semibold text-ink",
                  )}
                >
                  {l.label}
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/harshitwandhare/job-sentinel"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden rounded-lg border border-line px-3 py-1.5 text-sm text-ink transition-colors hover:border-ink/30 hover:bg-surface sm:block"
          >
            GitHub
          </a>
          <Link
            href="/studio"
            className="rounded-lg bg-ink px-3.5 py-1.5 text-sm font-medium text-white transition-colors hover:bg-night"
          >
            Open studio
          </Link>
        </div>
      </nav>
    </header>
  );
}
