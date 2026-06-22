/**
 * ATS platform detection from apply URLs.
 *
 * Knowing which ATS a company uses helps candidates prepare:
 * Workday has a notoriously long form; Ashby is smooth; Greenhouse
 * often requires cover letters. Detected from the apply URL already
 * present on each card — zero API calls.
 */

export type AtsPlatform =
  | "Greenhouse"
  | "Lever"
  | "Ashby"
  | "Workday"
  | "SmartRecruiters"
  | "BambooHR"
  | "Jobvite"
  | "iCIMS"
  | "Taleo"
  | "Rippling"
  | "Breezy";

interface AtsRule {
  platform: AtsPlatform;
  patterns: RegExp[];
}

const ATS_RULES: AtsRule[] = [
  {
    platform: "Greenhouse",
    patterns: [/boards\.greenhouse\.io\//i, /job-boards\.greenhouse\.io\//i, /grnh\.se\//i],
  },
  {
    platform: "Lever",
    patterns: [/jobs\.lever\.co\//i],
  },
  {
    platform: "Ashby",
    patterns: [/jobs\.ashbyhq\.com\//i],
  },
  {
    platform: "Workday",
    patterns: [/myworkdayjobs\.com\//i, /wd\d+\.myworkdayjobs\.com\//i],
  },
  {
    platform: "SmartRecruiters",
    patterns: [/careers\.smartrecruiters\.com\//i, /jobs\.smartrecruiters\.com\//i],
  },
  {
    platform: "BambooHR",
    patterns: [/bamboohr\.com\/jobs\//i, /\.bamboohr\.com\//i],
  },
  {
    platform: "Jobvite",
    patterns: [/jobs\.jobvite\.com\//i, /hire\.jobvite\.com\//i],
  },
  {
    platform: "iCIMS",
    patterns: [/icims\.com\//i],
  },
  {
    platform: "Taleo",
    patterns: [/taleo\.net\//i, /oraclecloud\.com\/hcmUI\/CandidateExperience/i],
  },
  {
    platform: "Rippling",
    patterns: [/ats\.rippling\.com\//i],
  },
  {
    platform: "Breezy",
    patterns: [/breezy\.hr\//i, /app\.breezy\.hr\//i],
  },
];

/** Map each platform to a muted colour token for the badge. */
export const ATS_COLORS: Record<AtsPlatform, string> = {
  Greenhouse: "bg-green-50 text-green-700 ring-green-200",
  Lever: "bg-blue-50 text-blue-700 ring-blue-200",
  Ashby: "bg-violet-50 text-violet-700 ring-violet-200",
  Workday: "bg-orange-50 text-orange-700 ring-orange-200",
  SmartRecruiters: "bg-sky-50 text-sky-700 ring-sky-200",
  BambooHR: "bg-lime-50 text-lime-700 ring-lime-200",
  Jobvite: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  iCIMS: "bg-teal-50 text-teal-700 ring-teal-200",
  Taleo: "bg-red-50 text-red-700 ring-red-200",
  Rippling: "bg-pink-50 text-pink-700 ring-pink-200",
  Breezy: "bg-cyan-50 text-cyan-700 ring-cyan-200",
};

/**
 * Detect the ATS platform from a job apply URL.
 * Returns null if no known platform is matched.
 */
export function detectAts(applyUrl: string | null | undefined): AtsPlatform | null {
  if (!applyUrl) return null;
  for (const rule of ATS_RULES) {
    if (rule.patterns.some((p) => p.test(applyUrl))) return rule.platform;
  }
  return null;
}
