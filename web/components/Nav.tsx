"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getAuthStatus, type AuthStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

const links = [
  { href: "/chat", label: "Chat" },
  { href: "/profile", label: "Profile" },
  { href: "/studio", label: "Studio" },
  { href: "/jobs", label: "Jobs" },
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

  useEffect(() => {
    getAuthStatus().then(setAuth);
  }, [pathname]);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 border-b backdrop-blur-md transition-colors duration-300",
        dark ? "border-white/10 bg-night/70" : "border-line/80 bg-bg/80",
      )}
    >
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3"
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
        <ul
          className={cn(
            "hidden items-center gap-6 text-sm sm:flex",
            dark ? "text-stone-300" : "text-muted",
          )}
        >
          {links.map((l) => {
            const active = pathname === l.href || pathname.startsWith(`${l.href}/`);
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "transition-colors",
                    dark ? "hover:text-white" : "hover:text-ink",
                    active && (dark ? "font-semibold text-white" : "font-semibold text-ink"),
                  )}
                >
                  {l.label}
                </Link>
              </li>
            );
          })}
          <li>
            <Link
              href="/login"
              aria-current={pathname === "/login" ? "page" : undefined}
              className={cn(
                "transition-colors",
                dark ? "hover:text-white" : "hover:text-ink",
                pathname === "/login" &&
                  (dark ? "font-semibold text-white" : "font-semibold text-ink"),
              )}
            >
              {auth?.user ? auth.user.username : "Sign in"}
            </Link>
          </li>
        </ul>
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/harshitwandhare/job-sentinel"
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "hidden rounded-lg border px-3 py-1.5 text-sm transition-colors sm:block",
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
              "rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors",
              dark
                ? "bg-white text-night hover:bg-stone-200"
                : "bg-ink text-white hover:bg-night",
            )}
          >
            Open studio
          </Link>
        </div>
      </nav>
    </header>
  );
}
