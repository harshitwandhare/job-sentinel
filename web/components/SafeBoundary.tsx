"use client";

import { Component, type ReactNode } from "react";

/**
 * Minimal error boundary for decorative/optional client widgets (e.g. the WebGL
 * hero). If the child throws — say, WebGL is unavailable on this GPU/headless —
 * we render the fallback (default: nothing) instead of taking down the page.
 */
export class SafeBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) return this.props.fallback ?? null;
    return this.props.children;
  }
}
