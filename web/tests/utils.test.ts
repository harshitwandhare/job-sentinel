import { describe, expect, it } from "vitest";

import { cn, externalUrl } from "@/lib/utils";

describe("externalUrl", () => {
  it("prefixes scheme-less URLs so they don't resolve as relative paths", () => {
    expect(externalUrl("linkedin.com/in/harshit")).toBe("https://linkedin.com/in/harshit");
  });

  it("leaves http(s) URLs untouched", () => {
    expect(externalUrl("https://github.com/x")).toBe("https://github.com/x");
    expect(externalUrl("http://legacy.example.com")).toBe("http://legacy.example.com");
  });

  it("passes through mailto and tel", () => {
    expect(externalUrl("mailto:a@b.c")).toBe("mailto:a@b.c");
    expect(externalUrl("tel:+1234567890")).toBe("tel:+1234567890");
  });

  it("returns empty for empty/whitespace input", () => {
    expect(externalUrl("")).toBe("");
    expect(externalUrl("   ")).toBe("");
  });
});

describe("cn", () => {
  it("merges and dedupes tailwind classes", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-ink", false && "hidden", "font-bold")).toBe("text-ink font-bold");
  });
});
