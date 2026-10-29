import { describe, expect, it } from "vitest";
import { hrefFor, selectionError, selectionFrom } from "./state";

const release = "a".repeat(64);
describe("shareable workbench state", () => {
  it("defaults to the final January purchase decision and pins the configured release", () => {
    const state = selectionFrom("/", release, "09:00");
    expect(state.view).toBe("decision");
    expect(state.filters.date).toBe("2026-01-31");
    expect(state.filters.release).toBe(release);
    expect(state.problem).toBeNull();
    const roundTrip = selectionFrom(hrefFor(state.view, state.filters), "b".repeat(64), "09:45");
    expect(roundTrip).toEqual(state);
  });
  it.each([
    "?cutoff_local=9:00",
    "?decision_date=2026-02-01",
    "?release_id=short",
    "?release_id=",
    "?cutoff_local=09:00&cutoff_local=09:00",
    "?unexpected=1",
  ])("explains an invalid address without silently replacing it: %s", (query) => {
    expect(selectionFrom(`/decision${query}`, release, "09:00").problem).not.toBeNull();
  });
  it("bounds accuracy dates and rejects reversed ranges", () => {
    const filters = selectionFrom(
      "/accuracy?decision_from=2026-01-31&decision_to=2026-01-01",
      release,
      "00:00",
    ).filters;
    expect(selectionError("accuracy", filters)).toMatch(/end date/);
    expect(selectionFrom("/accuracy?cutoff_local=00:00", release, "09:00").problem).toBeNull();
  });
  it("carries the same cutoff and release between all views with mode-specific dates", () => {
    const selected = selectionFrom(
      "/accuracy?cutoff_local=09:45&decision_from=2026-01-01&decision_to=2026-01-15",
      release,
      "09:00",
    );
    for (const view of ["decision", "accuracy", "methodology"] as const) {
      const state = selectionFrom(hrefFor(view, selected.filters), "b".repeat(64), "10:00");
      expect(state.filters.cutoff).toBe("09:45");
      expect(state.filters.release).toBe(release);
      expect(state.filters.from).toBe("2026-01-01");
      expect(state.filters.to).toBe("2026-01-15");
      expect(state.problem).toBeNull();
    }
  });
});
