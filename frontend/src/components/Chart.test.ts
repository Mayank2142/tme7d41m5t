import { describe, expect, it } from "vitest";
import { linePath } from "./Chart";

describe("native source-time chart gaps", () => {
  it("keeps valid zero generation and starts a new segment after a missing target", () => {
    const points = [0, null, 2000, 3000].map((value, index) => ({
      time: new Date(index * 3_600_000).toISOString(),
      value,
    }));
    const path = linePath(
      points,
      (instant) => instant / 3_600_000,
      (value) => value,
    );
    expect(path).toContain("M0.00,0.00");
    expect(path.match(/M/g)).toHaveLength(2);
    expect(path.match(/L/g)).toHaveLength(1);
    expect(path).not.toContain("L2.00");
  });
  it("leaves an entirely missing series without a fabricated zero line", () => {
    expect(
      linePath(
        [{ time: "2026-01-02T00:00:00Z", value: null }],
        (value) => value,
        (value) => value,
      ).trim(),
    ).toBe("");
  });
});
