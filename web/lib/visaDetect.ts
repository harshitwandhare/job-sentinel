/**
 * Visa sponsorship keyword detection from job description text.
 *
 * International students and visa holders typically need to find roles
 * that explicitly sponsor H-1B, OPT, CPT, etc. No ATS field covers
 * this — it's buried in the description. This module scans for the
 * presence and absence of known signals so we can surface a chip on
 * each card without any API call.
 *
 * Three outcomes:
 *   "sponsors"   — description explicitly mentions sponsorship
 *   "no_sponsor" — description explicitly says no sponsorship
 *   null         — no signal either way
 */

export type VisaSignal = "sponsors" | "no_sponsor" | null;

// Phrases that indicate sponsorship IS offered
const SPONSOR_PATTERNS = [
  /\bwill\s+sponsor\b/i,
  /\bsponsor(?:ship|s)?\s+(?:visa|h[\s-]?1b|opt|cpt|green\s+card|work\s+permit|work\s+authoriz)/i,
  /\b(?:visa|h[\s-]?1b|opt|cpt)\s+sponsor(?:ship|s)?/i,
  /\bopen\s+to\s+(?:visa\s+)?sponsor/i,
  /\bprovide\s+(?:visa\s+)?sponsor/i,
  /\beligible\s+for\s+(?:visa\s+)?sponsor/i,
];

// Phrases that indicate sponsorship is NOT offered
const NO_SPONSOR_PATTERNS = [
  /\bno\s+(?:visa\s+)?sponsor(?:ship)?(?:\s+(?:is|will\s+be)\s+(?:available|provided|offered))?\b/i,
  /\bunable\s+to\s+(?:offer|provide|support)\s+(?:visa\s+)?sponsor/i,
  /\bnot\s+(?:able|available)\s+to\s+sponsor/i,
  /\bcannot\s+sponsor\b/i,
  /\bwithout\s+(?:the\s+need\s+for\s+)?(?:visa\s+)?sponsor/i,
  /\bmust\s+(?:be\s+)?(?:authorized|eligible)\s+to\s+work\s+(?:in\s+the\s+(?:us|united\s+states))?\s*(?:without(?:\s+(?:current|future)\s+)?(?:employer\s+)?(?:visa\s+)?sponsor(?:ship)?)?/i,
  /\bauthorized\s+to\s+work\s+in\s+the\s+us\s+without\b/i,
];

export function detectVisaSignal(text: string): VisaSignal {
  if (!text) return null;

  // Check "no sponsor" first — it's more specific and should win
  for (const p of NO_SPONSOR_PATTERNS) {
    if (p.test(text)) return "no_sponsor";
  }
  for (const p of SPONSOR_PATTERNS) {
    if (p.test(text)) return "sponsors";
  }
  return null;
}

export const VISA_LABELS: Record<NonNullable<VisaSignal>, { short: string; title: string; classes: string }> = {
  sponsors: {
    short: "Sponsors visa",
    title: "This listing mentions visa sponsorship",
    classes: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
  no_sponsor: {
    short: "No sponsorship",
    title: "This listing explicitly does not offer visa sponsorship",
    classes: "bg-red-50 text-red-600 ring-red-200",
  },
};
