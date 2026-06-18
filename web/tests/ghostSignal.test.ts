import { describe, expect, it } from "vitest";

import { detectGhostSignal } from "../lib/ghostSignal";

// Pin "today" so age calculations are deterministic.
// Tests that exercise staleness pass a date well in the past.
const OLD_DATE = "2026-01-01"; // > 45 days before any plausible test run
const FRESH_DATE = new Date(Date.now() - 10 * 86_400_000).toISOString().slice(0, 10);

describe("detectGhostSignal", () => {
  it("returns null for a fresh posting with real content", () => {
    expect(
      detectGhostSignal({
        postedDate: FRESH_DATE,
        descriptionLength: 400,
        hasSalary: true,
        tagCount: 3,
      }),
    ).toBeNull();
  });

  it("returns 'stale' when the posting is older than 45 days", () => {
    expect(
      detectGhostSignal({
        postedDate: OLD_DATE,
        descriptionLength: 500,
        hasSalary: true,
        tagCount: 2,
      }),
    ).toBe("stale");
  });

  it("returns 'thin' when no date, no description, no salary, no tags", () => {
    expect(
      detectGhostSignal({
        postedDate: null,
        descriptionLength: 0,
        hasSalary: false,
        tagCount: 0,
      }),
    ).toBe("thin");
  });

  it("returns null when no date but description is rich", () => {
    expect(
      detectGhostSignal({
        postedDate: null,
        descriptionLength: 250,
        hasSalary: false,
        tagCount: 0,
      }),
    ).toBeNull();
  });

  it("stale takes priority over thin", () => {
    expect(
      detectGhostSignal({
        postedDate: OLD_DATE,
        descriptionLength: 0,
        hasSalary: false,
        tagCount: 0,
      }),
    ).toBe("stale");
  });

  it("returns null for an unparseable date string", () => {
    expect(
      detectGhostSignal({
        postedDate: "not-a-date",
        descriptionLength: 0,
        hasSalary: false,
        tagCount: 0,
      }),
    ).toBe("thin");
  });
});
