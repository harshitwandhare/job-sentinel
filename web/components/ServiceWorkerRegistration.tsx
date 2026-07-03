"use client";

import { useEffect } from "react";

/** Registers the offline app-shell worker; no-ops in the demo build or unsupported browsers. */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_DEMO === "1") return;
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  }, []);

  return null;
}
