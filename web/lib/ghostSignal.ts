/**
 * Ghost job heuristics — client-side freshness signals.
 *
 * Research shows 30–60 % of active listings are ghost jobs: postings left
 * live after a role is filled or cancelled. We surface two lightweight
 * signals based on data already in the card:
 *
 *   stale   — posting date is more than STALE_DAYS ago
 *   thin    — very short / absent description with no salary or tags
 *
 * These are hints, not verdicts. The chip copy is deliberately soft.
 */

const STALE_DAYS = 45;

export type GhostSignal = "stale" | "thin" | null;

function daysSince(dateStr: string): number | null {
  if (!dateStr) return null;
  // Accept ISO date strings ("2026-04-01") and ISO datetimes
  const parsed = new Date(dateStr);
  if (Number.isNaN(parsed.getTime())) return null;
  return Math.floor((Date.now() - parsed.getTime()) / 86_400_000);
}

export function detectGhostSignal(opts: {
  postedDate?: string | null;
  descriptionLength: number;
  hasSalary: boolean;
  tagCount: number;
}): GhostSignal {
  const { postedDate, descriptionLength, hasSalary, tagCount } = opts;

  if (postedDate) {
    const age = daysSince(postedDate);
    if (age !== null && age >= STALE_DAYS) return "stale";
  }

  // "thin" = no description AND no salary AND no tags
  if (descriptionLength < 30 && !hasSalary && tagCount === 0) return "thin";

  return null;
}

export const GHOST_LABELS: Record<NonNullable<GhostSignal>, { short: string; title: string }> = {
  stale: {
    short: "May be stale",
    title: `Posted more than ${STALE_DAYS} days ago — role may already be filled`,
  },
  thin: {
    short: "Thin listing",
    title: "Very little detail — could be a placeholder or ghost posting",
  },
};
