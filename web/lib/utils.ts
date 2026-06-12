import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind class names, de-duplicating conflicts. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Make a user-entered link safe to use in an href.
 * Profiles often store scheme-less URLs ("linkedin.com/in/me"), which the
 * browser would otherwise resolve relative to the current page.
 */
export function externalUrl(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (trimmed.startsWith("mailto:") || trimmed.startsWith("tel:")) return trimmed;
  return `https://${trimmed}`;
}
