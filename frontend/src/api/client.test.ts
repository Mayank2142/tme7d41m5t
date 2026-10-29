import { afterEach, describe, expect, it, vi } from "vitest";
import { type Configuration, loadConfiguration } from "./client";

function readyConfiguration(): Configuration {
  return {
    application: "Wind Desk",
    version: "0.1.0",
    stage: "data_ready",
    build_sha: "test",
    default_cutoff_local: "09:00",
    data_attribution: "Required data attribution",
    data_licence_url:
      "https://www.elexon.co.uk/bsc/data/balancing-mechanism-reporting-agent/copyright-licence-bmrs-data/",
    policy: {
      policy_version: "january_decisions_v1",
      timezone: "Europe/London",
      decision_from: "2026-01-01",
      decision_to: "2026-01-31",
      delivery_from: "2026-01-02",
      delivery_to: "2026-02-01",
      comparison_policy: "source_timestamp_v1",
      availability_model: "source_publication_time",
      forecast_cadence_minutes: 60,
      actual_interval_minutes: 30,
      cutoff_is_illustrative: true,
    },
    dataset: {
      status: "available",
      release_id: "a".repeat(64),
      forecast_versions: 19856,
      actual_versions: 1488,
      quality_status: "complete",
      code: "OK",
    },
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("configuration service failure boundaries", () => {
  it("accepts a validated data release instead of treating it as a missing dataset", async () => {
    const body = readyConfiguration();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body))));
    await expect(loadConfiguration()).resolves.toEqual(body);
  });

  it("rejects contradictory readiness metadata", async () => {
    const body = readyConfiguration();
    body.stage = "foundation";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body))));
    await expect(loadConfiguration()).rejects.toThrow("unsupported configuration contract");
  });

  it("rejects negative source counts", async () => {
    const body = readyConfiguration();
    body.dataset.actual_versions = -1;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body))));
    await expect(loadConfiguration()).rejects.toThrow("unsupported configuration contract");
  });
  it("explains an unavailable API instead of treating its body as configuration", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("unavailable", { status: 503 })));
    await expect(loadConfiguration()).rejects.toThrow("HTTP 503");
  });

  it.each([null, {}, { stage: "foundation" }, { stage: "future_contract" }])(
    "rejects an incomplete or incompatible body so the UI can offer a retry",
    async (body) => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body))));
      await expect(loadConfiguration()).rejects.toThrow("unsupported configuration contract");
    },
  );
});
