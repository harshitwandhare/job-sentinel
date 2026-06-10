"use client";

import { motion, useScroll, useSpring } from "framer-motion";

/** Thin brand progress bar pinned to the top of the viewport. */
export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 28, restDelta: 0.001 });
  return (
    <motion.div
      aria-hidden="true"
      className="fixed inset-x-0 top-0 z-[80] h-0.5 origin-left bg-gradient-to-r from-brand-600 via-brand-500 to-brand-400"
      style={{ scaleX }}
    />
  );
}
