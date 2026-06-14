import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { CommandPalette } from "@/components/CommandPalette";
import { CustomCursor } from "@/components/CustomCursor";
import { Nav } from "@/components/Nav";
import { ScrollProgress } from "@/components/ScrollProgress";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL("https://github.com/harshitwandhare/job-sentinel"),
  title: {
    default: "Job Sentinel — local-first job monitoring & AI résumé studio",
    template: "%s · Job Sentinel",
  },
  description:
    "Monitor job portals, track every posting, and generate ATS-ready résumés tailored " +
    "by a local LLM. Open source, private by default — your data never leaves your machine.",
  icons: {
    icon: [
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  openGraph: {
    title: "Job Sentinel",
    description:
      "Local-first job monitoring, tracking, and AI resume tooling for your own machine.",
    images: [{ url: "/brand/sentinel.png", width: 1024, height: 1024, alt: "Job Sentinel logo" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#0c0a09",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="has-custom-cursor font-sans">
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-brand focus:px-4 focus:py-2 focus:text-white"
        >
          Skip to content
        </a>
        <ScrollProgress />
        <CustomCursor />
        <CommandPalette />
        {process.env.NEXT_PUBLIC_DEMO === "1" && (
          <div className="bg-brand px-4 py-1.5 text-center text-xs font-medium text-white">
            Live demo — showing sample data.{" "}
            <a
              href="https://github.com/harshitwandhare/job-sentinel#-quick-start"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              Run it locally
            </a>{" "}
            for your real jobs, profile, and a private local model.
          </div>
        )}
        <Nav />
        <main id="content" className="min-h-screen">
          {children}
        </main>
        <footer className="border-t border-line bg-surface">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-sm text-muted sm:flex-row">
            <p className="flex items-center gap-2">
              <img
                src="/brand/sentinel.png"
                alt=""
                className="h-7 w-7 rounded-md object-cover"
                aria-hidden="true"
              />
              <span>
              <span className="font-semibold text-ink">Job Sentinel</span> — local-first, open
              source. Your data stays on your machine.
              </span>
            </p>
            <div className="flex items-center gap-5">
              <a
                href="https://github.com/harshitwandhare/job-sentinel"
                className="hover:text-ink"
              >
                GitHub
              </a>
              <a href="https://pypi.org/project/job-sentinel/" className="hover:text-ink">
                PyPI
              </a>
              <span aria-hidden="true">MIT License</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
