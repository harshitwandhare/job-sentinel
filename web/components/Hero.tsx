"use client";

import { motion } from "framer-motion";
import dynamic from "next/dynamic";
import Link from "next/link";

import { Button } from "@/components/ui/button";

// WebGL must run client-side only; load it lazily so it never blocks SSR/paint.
const Hero3D = dynamic(() => import("@/components/Hero3D"), { ssr: false });

export function Hero() {
  return (
    <section className="relative mx-auto max-w-5xl overflow-hidden px-5 py-24 text-center">
      <Hero3D />
      <motion.h1
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="bg-gradient-to-br from-white to-neutral-400 bg-clip-text text-5xl font-bold tracking-tight text-transparent sm:text-6xl"
      >
        Your career, on autopilot — locally.
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.12 }}
        className="mx-auto mt-6 max-w-2xl text-lg text-neutral-400"
      >
        Monitor job portals, track every posting, and generate ATS-ready résumés tailored to
        each role — powered by a local LLM. Private by default; your data never leaves your
        machine.
      </motion.p>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.24 }}
        className="mt-10 flex items-center justify-center gap-4"
      >
        <Link href="/profile">
          <Button size="lg">View profile</Button>
        </Link>
        <Link href="/jobs">
          <Button size="lg" variant="outline">
            Browse jobs
          </Button>
        </Link>
      </motion.div>
    </section>
  );
}
