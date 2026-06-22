import { describe, expect, it } from "vitest";

import { detectAts } from "../lib/atsDetect";

describe("detectAts", () => {
  it("detects Greenhouse board URLs", () => {
    expect(detectAts("https://boards.greenhouse.io/acme/jobs/123")).toBe("Greenhouse");
    expect(detectAts("https://job-boards.greenhouse.io/acme/jobs/456")).toBe("Greenhouse");
    expect(detectAts("https://grnh.se/abc123")).toBe("Greenhouse");
  });

  it("detects Lever", () => {
    expect(detectAts("https://jobs.lever.co/acme/abc-123")).toBe("Lever");
  });

  it("detects Ashby", () => {
    expect(detectAts("https://jobs.ashbyhq.com/acme/role-slug")).toBe("Ashby");
  });

  it("detects Workday", () => {
    expect(detectAts("https://acme.myworkdayjobs.com/en-US/careers")).toBe("Workday");
    expect(detectAts("https://acme.wd1.myworkdayjobs.com/careers/")).toBe("Workday");
  });

  it("detects SmartRecruiters", () => {
    expect(detectAts("https://careers.smartrecruiters.com/Acme/")).toBe("SmartRecruiters");
  });

  it("detects BambooHR", () => {
    expect(detectAts("https://acme.bamboohr.com/jobs/view.php?id=1")).toBe("BambooHR");
  });

  it("detects Jobvite", () => {
    expect(detectAts("https://jobs.jobvite.com/acme/job/abc123")).toBe("Jobvite");
  });

  it("detects iCIMS", () => {
    expect(detectAts("https://careers-acme.icims.com/jobs/123/job")).toBe("iCIMS");
  });

  it("detects Taleo", () => {
    expect(detectAts("https://acme.taleo.net/careersection/apply")).toBe("Taleo");
  });

  it("returns null for unknown URLs", () => {
    expect(detectAts("https://acme.com/careers")).toBeNull();
    expect(detectAts("https://linkedin.com/jobs/view/123")).toBeNull();
  });

  it("returns null for empty / null input", () => {
    expect(detectAts(null)).toBeNull();
    expect(detectAts(undefined)).toBeNull();
    expect(detectAts("")).toBeNull();
  });
});
