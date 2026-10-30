// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { createHash } from "node:crypto";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Configuration } from "./api/client";
import type { DecisionResponse } from "./api/types";
import {
  accuracy,
  apiResponse,
  configuration,
  decision,
  january1,
  later,
  month,
  quality,
} from "./test/fixtures";

let client: QueryClient;
let override: ((url: URL) => Response | Promise<Response> | undefined) | undefined;
let fetchMock: ReturnType<typeof vi.fn>;
function repin<T extends typeof decision | typeof accuracy>(source: T, release: string): T {
  const body = structuredClone(source);
  body.context.release_id = release;
  body.analysis_context_id = createHash("sha256")
    .update(JSON.stringify(body.context, Object.keys(body.context).sort()))
    .digest("hex");
  body.source.data_quality_url = `/api/v1/data-quality?release_id=${release}`;
  const link = new URL(body.export_url, "http://localhost");
  link.searchParams.set("release_id", release);
  link.searchParams.set("expected_context_id", body.analysis_context_id);
  body.export_url = link.pathname + link.search;
  return body;
}
function responseFor(url: URL): Response {
  if (url.pathname === "/api/v1/config") return apiResponse(configuration);
  if (url.pathname === "/api/v1/decision-view") {
    const source =
      url.searchParams.get("decision_date") === "2026-01-01"
        ? january1
        : url.searchParams.get("cutoff_local") === "09:45"
          ? later
          : decision;
    return apiResponse(
      repin(source, url.searchParams.get("release_id") ?? configuration.dataset.release_id),
    );
  }
  if (url.pathname === "/api/v1/accuracy")
    return apiResponse(url.searchParams.get("decision_to") === "2026-01-01" ? accuracy : month);
  if (url.pathname === "/api/v1/data-quality") return apiResponse(quality);
  return apiResponse(
    { code: "NOT_FOUND", message: "Unknown test route", request_id: "test-request" },
    404,
  );
}
function mount(path = "/") {
  window.history.replaceState(null, "", path);
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}
async function ready() {
  await screen.findByText("24 / 24");
}
beforeEach(() => {
  override = undefined;
  client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: Infinity, refetchOnWindowFocus: false },
    },
  });
  fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = new URL(String(input), window.location.origin);
    return Promise.resolve(override?.(url) ?? responseFor(url));
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  cleanup();
  client.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("analyst workflow", () => {
  it("can compact the photographic header without changing the selected analysis or fetching new data", async () => {
    mount();
    await ready();
    const selected = window.location.href;
    const requests = fetchMock.mock.calls.length;
    const compact = screen.getByRole("button", { name: "Compact header" });
    expect(compact).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByText(/AI-generated/i)).not.toBeInTheDocument();
    fireEvent.click(compact);
    expect(compact).toHaveAttribute("aria-pressed", "true");
    expect(window.location.href).toBe(selected);
    expect(fetchMock.mock.calls.length).toBe(requests);
    expect(screen.getByRole("button", { name: /Download CSV/ })).toBeEnabled();
    fireEvent.click(compact);
    expect(compact).toHaveAttribute("aria-pressed", "false");
  });
  it("pins the initial release, includes February delivery, and keeps Decision forecast-only", async () => {
    mount();
    await ready();
    expect(window.location.pathname).toBe("/decision");
    expect(new URLSearchParams(window.location.search).get("release_id")).toBe(
      configuration.dataset.release_id,
    );
    expect(screen.getByText("1 Feb 2026")).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "Inspect wind target" })).toHaveAttribute(
      "max",
      "23",
    );
    expect(screen.queryByText("Mean absolute error")).not.toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url]) => String(url).includes("accuracy") || String(url).includes("data-quality"),
      ),
    ).toBe(false);
  });
  it("marks draft filters and hides old results while the next request is pending", async () => {
    let resolve: (response: Response) => void = () => undefined;
    override = (url) =>
      url.pathname === "/api/v1/decision-view" && url.searchParams.get("cutoff_local") === "09:45"
        ? new Promise<Response>((done) => {
            resolve = done;
          })
        : undefined;
    mount();
    await ready();
    fireEvent.change(screen.getByLabelText("Desk cutoff · GMT"), { target: { value: "09:45" } });
    expect(screen.getByText("Unapplied changes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download CSV/ })).toBeDisabled();
    expect(screen.getAllByText("09:00 GMT", { selector: "strong" })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Apply selection" }));
    await screen.findByText("Loading the selected analysis…");
    expect(screen.queryByText("24 / 24")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Download CSV/ })).not.toBeInTheDocument();
    await act(async () => resolve(apiResponse(later)));
    await ready();
    expect(screen.getAllByText("09:45 GMT", { selector: "strong" })).toHaveLength(1);
    expect(new URLSearchParams(window.location.search).get("cutoff_local")).toBe("09:45");
    expect(screen.getByRole("button", { name: /Download CSV/ })).toBeEnabled();
  });
  it("renders retrospective metrics, original actuals, daily review, and the reconciled ledger", async () => {
    mount();
    await ready();
    fireEvent.click(screen.getByRole("link", { name: "Forecast accuracy" }));
    await screen.findByRole("heading", { name: "Mean absolute error" });
    expect(screen.getByText("2,022.5")).toBeInTheDocument();
    expect(screen.getByText("744 / 744 paired targets")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Signed forecast errors" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Daily accuracy" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Coverage ledger" })).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "Inspect wind target" })).toHaveAttribute(
      "max",
      "743",
    );
  });
  it("loads release-pinned source provenance and describes source-time limitations", async () => {
    mount();
    await ready();
    fireEvent.click(screen.getByRole("link", { name: "Data & methodology" }));
    await screen.findByText("19,856");
    expect(
      screen.getByRole("heading", { name: "Matching timestamps, explicit limits" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/does not prove January receipt/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open Elexon response ↗" })).toHaveLength(10);
    expect(
      screen.getByRole("img", { name: "Wind turbines on green coastal hills" }),
    ).toHaveAttribute("loading", "lazy");
    expect(screen.queryByRole("button", { name: /Download CSV/ })).not.toBeInTheDocument();
  });
  it("shows an explained failure and retries without losing the URL selection", async () => {
    let fail = true;
    override = (url) =>
      fail && url.pathname === "/api/v1/decision-view"
        ? apiResponse(
            {
              code: "DATABASE_UNAVAILABLE",
              message: "Stored source data is unavailable.",
              request_id: "safe-reference",
            },
            503,
          )
        : undefined;
    mount();
    await screen.findByText("Could not load this selection");
    expect(screen.getByText(/safe-reference/)).toBeInTheDocument();
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await ready();
    expect(new URLSearchParams(window.location.search).get("decision_date")).toBe("2026-01-31");
  });
  it("labels a failed refresh, retains the same result, and disables its export", async () => {
    mount();
    await ready();
    override = (url) =>
      url.pathname === "/api/v1/decision-view"
        ? apiResponse(
            {
              code: "DATABASE_UNAVAILABLE",
              message: "Refresh unavailable.",
              request_id: "refresh-reference",
            },
            503,
          )
        : undefined;
    fireEvent.click(screen.getByRole("button", { name: "↻ Refresh analysis" }));
    await screen.findByText("Refresh failed; the last successful result remains below");
    expect(screen.getByText("24 / 24")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download CSV/ })).toBeDisabled();
  });
  it("recovers from a stale download context through a visible reload action", async () => {
    override = (url) =>
      url.pathname === "/api/v1/export.csv"
        ? apiResponse(
            {
              code: "ANALYSIS_CONTEXT_MISMATCH",
              message: "The analysis context changed. Refresh the analysis before downloading.",
              request_id: "download-reference",
            },
            409,
          )
        : undefined;
    mount();
    await ready();
    fireEvent.click(screen.getByRole("button", { name: /Download CSV/ }));
    await screen.findByText(
      "The analysis context changed. Refresh the analysis before downloading.",
    );
    expect(screen.getByRole("button", { name: "Reload analysis" })).toBeInTheDocument();
    const url = fetchMock.mock.calls
      .map(([input]) => String(input))
      .find((input) => input.startsWith("/api/v1/export.csv"));
    expect(
      new URL(String(url), window.location.origin).searchParams.get("expected_context_id"),
    ).toBe(decision.analysis_context_id);
  });
  it("does not silently replace a release pinned in a shared link", async () => {
    const older = "b".repeat(64);
    mount(`/decision?decision_date=2026-01-31&cutoff_local=09:00&release_id=${older}`);
    await ready();
    expect(screen.getByText("Newer data available")).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get("release_id")).toBe(older);
    fireEvent.click(screen.getByRole("button", { name: "Use latest data" }));
    await waitFor(() =>
      expect(new URLSearchParams(window.location.search).get("release_id")).toBe(
        configuration.dataset.release_id,
      ),
    );
    await ready();
  });
  it("rejects bad shared filters before analysis requests and can reset them", async () => {
    mount("/decision?decision_date=2026-02-01");
    await screen.findByText("Check this selection");
    expect(fetchMock.mock.calls.every(([url]) => String(url) === "/api/v1/config")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Reset to January defaults" }));
    await ready();
  });
  it("handles browser-history selections and exposes exact chart data without hover", async () => {
    mount();
    await ready();
    await act(async () => {
      window.history.pushState(
        null,
        "",
        `/decision?decision_date=2026-01-01&release_id=${configuration.dataset.release_id}&cutoff_local=09:00`,
      );
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await screen.findByText("18,781 MW");
    fireEvent.change(screen.getByRole("slider", { name: "Inspect wind target" }), {
      target: { value: "1" },
    });
    expect(screen.getByText("Target 2 / 24")).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "Inspect wind target" })).toHaveAttribute(
      "aria-valuetext",
      expect.stringContaining("18,793 MW"),
    );
  });
  it("renders unavailable-dataset and zero-coverage states without invented zeros", async () => {
    const unavailable = structuredClone(configuration) as unknown as Configuration;
    unavailable.dataset.release_id = null;
    unavailable.dataset.status = "not_initialized";
    unavailable.stage = "foundation";
    unavailable.dataset.quality_status = null;
    override = (url) => (url.pathname === "/api/v1/config" ? apiResponse(unavailable) : undefined);
    mount();
    await screen.findByText("January source data is unavailable");
    expect(fetchMock.mock.calls).toHaveLength(1);
    cleanup();
    client.clear();
    const missing = structuredClone(decision) as unknown as DecisionResponse;
    for (const point of missing.analysis.points) {
      point.forecast.state = "missing";
      point.forecast.generation_mw = null;
      point.forecast.publication_utc = null;
      point.forecast.source_version_ids = [];
      point.forecast.reason = "NO_PRE_CUTOFF_PUBLICATION";
      point.age_at_cutoff_seconds = null;
    }
    missing.analysis.coverage = {
      expected: 24,
      valid: 0,
      missing: 24,
      invalid: 0,
      valid_percent: 0,
    };
    for (const key of Object.keys(missing.analysis.summary))
      Reflect.set(missing.analysis.summary, key, null);
    override = (url) =>
      url.pathname === "/api/v1/decision-view" ? apiResponse(missing) : undefined;
    mount();
    await screen.findByText("0 / 24");
    expect(screen.getByText("No valid points to plot")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
  it("keeps a partial forecast visible with an explicit invalid latest target", async () => {
    const partial = structuredClone(decision) as unknown as DecisionResponse;
    partial.analysis.points[0].forecast = {
      ...partial.analysis.points[0].forecast,
      state: "invalid",
      generation_mw: null,
      reason: "NULL_GENERATION",
    };
    partial.analysis.coverage = {
      expected: 24,
      valid: 23,
      invalid: 1,
      missing: 0,
      valid_percent: (100 * 23) / 24,
    };
    partial.analysis.summary.mean_reported_mw =
      partial.analysis.points
        .slice(1)
        .reduce((sum, point) => sum + Number(point.forecast.generation_mw), 0) / 23;
    partial.analysis.summary.maximum_reported_mw = Math.max(
      ...partial.analysis.points.slice(1).map((point) => Number(point.forecast.generation_mw)),
    );
    override = (url) =>
      url.pathname === "/api/v1/decision-view" ? apiResponse(partial) : undefined;
    mount();
    await screen.findByText("23 / 24");
    expect(screen.getByText("Partial coverage")).toBeInTheDocument();
    expect(screen.getByText("0 missing · 1 invalid")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download CSV/ })).toBeEnabled();
  });
});
