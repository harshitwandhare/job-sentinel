import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { CustomCursor } from "@/components/CustomCursor";
import { Nav } from "@/components/Nav";
import { ScrollProgress } from "@/components/ScrollProgress";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });

export const metadata: Metadata = {
  title: {
    default: "Job Sentinel — local-first job monitoring & AI résumé studio",
    template: "%s · Job Sentinel",
  },
  description:
    "Monitor job portals, track every posting, and generate ATS-ready résumés tailored " +
    "by a local LLM. Open source, private by default — your data never leaves your machine.",
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
        <Nav />
        <main id="content" className="min-h-screen">
          {children}
        </main>
        <footer className="border-t border-line bg-surface">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-sm text-muted sm:flex-row">
            <p>
              <span className="font-semibold text-ink">Job Sentinel</span> — local-first, open
              source. Your data stays on your machine.
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
