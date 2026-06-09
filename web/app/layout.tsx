import type { Metadata } from "next";

import { Nav } from "@/components/Nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Job Sentinel",
  description: "Local-first job monitoring + ATS résumé studio.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <Nav />
        <main className="min-h-screen">{children}</main>
        <footer className="border-t border-neutral-800 py-6 text-center text-xs text-neutral-500">
          Local-first · open source · your data stays on your machine
        </footer>
      </body>
    </html>
  );
}
