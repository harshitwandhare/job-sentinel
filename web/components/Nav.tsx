import Link from "next/link";

const links = [
  { href: "/", label: "Home" },
  { href: "/profile", label: "Profile" },
  { href: "/profile/edit", label: "Edit" },
  { href: "/studio", label: "Studio" },
  { href: "/jobs", label: "Jobs" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-10 border-b border-neutral-800 bg-neutral-950/80 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
        <Link href="/" className="font-semibold text-neutral-100">
          🛡 Job Sentinel
        </Link>
        <ul className="flex items-center gap-5 text-sm text-neutral-300">
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="hover:text-white">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
