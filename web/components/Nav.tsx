import Link from "next/link";

const links = [
  { href: "/chat", label: "Chat" },
  { href: "/profile", label: "Profile" },
  { href: "/profile/edit", label: "Edit" },
  { href: "/studio", label: "Studio" },
  { href: "/jobs", label: "Jobs" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-line/80 bg-bg/80 backdrop-blur-md">
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3"
      >
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight text-ink">
          <span
            aria-hidden="true"
            className="grid h-7 w-7 place-items-center rounded-lg bg-night text-sm text-brand-400"
          >
            ◈
          </span>
          Job Sentinel
        </Link>
        <ul className="hidden items-center gap-6 text-sm text-muted sm:flex">
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="transition-colors hover:text-ink">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/harshitwandhare/job-sentinel"
            className="hidden rounded-lg border border-line px-3 py-1.5 text-sm text-ink transition-colors hover:border-ink/30 hover:bg-surface sm:block"
          >
            GitHub ↗
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
