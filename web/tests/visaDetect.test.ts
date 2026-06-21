import { describe, expect, it } from "vitest";

import { detectVisaSignal } from "../lib/visaDetect";

describe("detectVisaSignal", () => {
  it("returns null for text with no sponsorship mention", () => {
    expect(detectVisaSignal("We are looking for a senior engineer.")).toBeNull();
    expect(detectVisaSignal("")).toBeNull();
  });

  it("detects positive sponsorship signals", () => {
    expect(detectVisaSignal("We will sponsor H-1B visas for qualified candidates.")).toBe("sponsors");
    expect(detectVisaSignal("The company provides visa sponsorship for this role.")).toBe("sponsors");
    expect(detectVisaSignal("We are open to visa sponsorship for exceptional candidates.")).toBe("sponsors");
    expect(detectVisaSignal("OPT sponsorship available.")).toBe("sponsors");
  });

  it("detects negative sponsorship signals", () => {
    expect(detectVisaSignal("No visa sponsorship is available for this position.")).toBe("no_sponsor");
    expect(detectVisaSignal("We are unable to offer visa sponsorship.")).toBe("no_sponsor");
    expect(detectVisaSignal("Candidates must be authorized to work in the US without employer sponsorship.")).toBe(
      "no_sponsor",
    );
    expect(detectVisaSignal("Cannot sponsor work visas at this time.")).toBe("no_sponsor");
  });

  it("no_sponsor takes priority when both signals appear", () => {
    const text =
      "We sponsor great talent but unfortunately no visa sponsorship is available for this role.";
    expect(detectVisaSignal(text)).toBe("no_sponsor");
  });

  it("is case-insensitive", () => {
    expect(detectVisaSignal("NO VISA SPONSORSHIP OFFERED")).toBe("no_sponsor");
    expect(detectVisaSignal("WILL SPONSOR H1B")).toBe("sponsors");
  });
});
