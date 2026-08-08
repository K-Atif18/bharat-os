import { describe, expect, it } from "vitest";

import {
  formatConfidence,
  formatDeadline,
  formatRupees,
  humaniseField,
  stalenessNote,
} from "@/lib/format";

describe("formatRupees", () => {
  it("uses crore for large amounts", () => {
    expect(formatRupees(100_000_000)).toBe("₹10 crore");
    expect(formatRupees(15_000_000)).toBe("₹1.5 crore");
  });

  it("uses lakh for mid amounts", () => {
    expect(formatRupees(2_000_000)).toBe("₹20 lakh");
    expect(formatRupees(1_250_000)).toBe("₹12.5 lakh");
  });

  it("distinguishes an unspecified benefit from a zero benefit", () => {
    // A registration that pays nothing is not the same as an unknown amount.
    expect(formatRupees(null)).toBe("Not specified");
    expect(formatRupees(0)).toBe("No direct monetary benefit");
  });
});

describe("formatConfidence", () => {
  it("renders a rounded percentage", () => {
    expect(formatConfidence(0.874)).toBe("87%");
    expect(formatConfidence(1)).toBe("100%");
    expect(formatConfidence(0)).toBe("0%");
  });
});

describe("humaniseField", () => {
  it("maps internal names to readable labels", () => {
    expect(humaniseField("annual_turnover_inr")).toBe("annual turnover");
    expect(humaniseField("entity_age_years")).toBe("incorporation date");
  });

  it("falls back to de-underscored text for unknown fields", () => {
    expect(humaniseField("some_new_field")).toBe("some new field");
  });
});

describe("stalenessNote", () => {
  it("stays silent for fresh data", () => {
    expect(stalenessNote(10)).toBeNull();
  });

  it("warns once past the threshold", () => {
    expect(stalenessNote(120)).toContain("120 days ago");
    expect(stalenessNote(400)).toContain("over a year");
  });
});

describe("formatDeadline", () => {
  it("returns null when there is no deadline", () => {
    expect(formatDeadline(null)).toBeNull();
  });

  it("counts down to a future deadline", () => {
    const future = new Date(Date.now() + 19 * 86_400_000).toISOString();
    expect(formatDeadline(future)).toMatch(/19 days left/);
  });

  it("marks a past deadline as closed", () => {
    const past = new Date(Date.now() - 5 * 86_400_000).toISOString();
    expect(formatDeadline(past)).toMatch(/^Closed/);
  });
});
