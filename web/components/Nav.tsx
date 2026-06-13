"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { OPEN_EVENT } from "@/components/CommandPalette";
import { getAuthStatus, type AuthStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

const links = [
  { href: "/search", label: "Search" },
  { href: "/chat", label: "Chat" },
  { href: "/profile", label: "Profile" },
  { href: "/studio", label: "Studio" },
  { href: "/jobs", label: "Jobs" },
  { href: "/settings", label: "Settings" },
];

const NAV_HEIGHT = 56;

/**
 * True while a `[data-nav-theme="dark"]` section sits under the nav bar, so
 * the bar can flip to light text/borders over dark backgrounds (hero,
 * engineering section) and back to dark-on-light everywhere else.
 */
function useOverDarkSection(pathname: string): boolean {
  const [overDark, setOverDark] = useState(false);

  useEffect(() => {
    let raf = 0;
    const update = () => {
      raf = 0;
      let dark = false;
      document.querySelectorAll<HTMLElement>("[data-nav-theme='dark']").forEach((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.top <= NAV_HEIGHT && rect.bottom >= NAV_HEIGHT / 2) dark = true;
      });
      setOverDark(dark);
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [pathname]);

  return overDark;
}

export function Nav() {
  const pathname = usePathname();
  const dark = useOverDarkSection(pathname);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    getAuthStatus().then(setAuth);
    setOpen(false); // close the mobile menu on navigation
  }, [pathname]);

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  const accountLabel = auth?.user ? auth.user.username : "Sign in";

  return (
    <header
      className={cn(
        "sticky top-0 z-50 border-b backdrop-blur-md transition-colors duration-300",
        dark ? "border-white/10 bg-night/70" : "border-line/80 bg-bg/80",
      )}
    >
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6"
      >
        <Link
          href="/"
          className={cn(
            "flex items-center gap-2 font-semibold tracking-tight transition-colors",
            dark ? "text-white" : "text-ink",
          )}
        >
          <img
            src="/brand/sentinel.png"
            alt=""
            className="h-8 w-8 rounded-lg border border-white/10 bg-night object-cover shadow-sm"
            aria-hidden="true"
          />
          Job Sentinel
        </Link>

        {/* Desktop links */}
        <ul
          className={cn(
            "hidden items-center gap-6 text-sm md:flex",
            dark ? "text-stone-300" : "text-muted",
          )}
        >
          {[...links, { href: "/login", label: accountLabel }].map((l) => (
            <li key={l.href}>
              <Link
                href={l.href}
                aria-current={isActive(l.href) ? "page" : undefined}
                className={cn(
                  "transition-colors",
                  dark ? "hover:text-white" : "hover:text-ink",
                  isActive(l.href) &&
                    (dark ? "font-semibold text-white" : "font-semibold text-ink"),
                )}
              >
                {l.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={() => window.dispatchEvent(new CustomEvent(OPEN_EVENT))}
            aria-label="Open command palette"
            className={cn(
              "hidden items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors md:flex",
              dark
                ? "border-white/20 text-stone-300 hover:bg-white/10 hover:text-white"
                : "border-line text-muted hover:border-ink/30 hover:text-ink",
            )}
          >
            <span>Search</span>
            <kbd
              className={cn(
                "rounded border px-1.5 font-mono text-[10px]",
                dark ? "border-white/20" : "border-line",
              )}
            >
              ⌘K
            </kbd>
          </button>
          <a
            href="https://github.com/harshitwandhare/job-sentinel"
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "hidden rounded-lg border px-3 py-1.5 text-sm transition-colors md:block",
              dark
                ? "border-white/20 text-white hover:bg-white/10"
                : "border-line text-ink hover:border-ink/30 hover:bg-surface",
            )}
          >
            GitHub
          </a>
          <Link
            href="/studio"
            className={cn(
              "hidden rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors sm:block",
              dark
                ? "bg-white text-night hover:bg-stone-200"
                : "bg-ink text-white hover:bg-night",
            )}
          >
            Open studio
          </Link>

          {/* Mobile menu toggle */}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-lg border transition-colors md:hidden",
              dark
                ? "border-white/20 text-white hover:bg-white/10"
                : "border-line text-ink hover:bg-surface",
            )}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              className="h-5 w-5"
              aria-hidden="true"
            >
              {open ? (
                <path d="M6 6l12 12M18 6L6 18" />
              ) : (
                <path d="M4 7h16M4 12h16M4 17h16" />
              )}
            </svg>
          </button>
        </div>
      </nav>

      {/* Mobile menu panel */}
      {open && (
        <div
          id="mobile-menu"
          className={cn(
            "border-t md:hidden",
            dark ? "border-white/10 bg-night/95" : "border-line bg-bg/95",
          )}
        >
          <ul className="space-y-1 px-4 py-3">
            {[...links, { href: "/login", label: accountLabel }].map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  aria-current={isActive(l.href) ? "page" : undefined}
                  className={cn(
                    "block rounded-lg px-3 py-2.5 text-sm transition-colors",
                    dark
                      ? "text-stone-300 hover:bg-white/10 hover:text-white"
                      : "text-muted hover:bg-surface hover:text-ink",
                    isActive(l.href) &&
                      (dark ? "font-semibold text-white" : "font-semibold text-ink"),
                  )}
                >
                  {l.label}
                </Link>
              </li>
            ))}
            <li>
              <a
                href="https://github.com/harshitwandhare/job-sentinel"
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  "block rounded-lg px-3 py-2.5 text-sm transition-colors",
                  dark
                    ? "text-stone-300 hover:bg-white/10 hover:text-white"
                    : "text-muted hover:bg-surface hover:text-ink",
                )}
              >
                GitHub ↗
              </a>
            </li>
          </ul>
        </div>
      )}
    </header>
  );
}
