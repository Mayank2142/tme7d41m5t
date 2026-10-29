import { afterEach, describe, expect, it, vi } from "vitest";
import { accuracy, apiResponse, decision, filters, month, quality } from "../test/fixtures";
import { downloadCsv, loadAccuracy, loadDecision, loadQuality, ServiceError } from "./analysis";

afterEach(() => vi.unstubAllGlobals());
describe("analysis contracts and context integrity", () => {
  it("accepts the frozen real decision, single-day accuracy, month and quality responses", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    fetch.mockResolvedValueOnce(apiResponse(decision));
    expect((await loadDecision(filters)).analysis.coverage.valid).toBe(24);
    fetch.mockResolvedValueOnce(apiResponse(accuracy));
    expect(
      (await loadAccuracy({ ...filters, to: "2026-01-01" })).analysis.days[0].points[0].error_mw,
    ).toBe(3553);
    fetch.mockResolvedValueOnce(apiResponse(month));
    expect((await loadAccuracy(filters)).analysis.metrics.paired_targets).toBe(744);
    fetch.mockResolvedValueOnce(apiResponse(quality));
    expect((await loadQuality(filters.release)).raw_batches).toHaveLength(10);
  });
  it.each([
    "release",
    "cutoff",
    "publication",
    "download",
    "future-actual",
    "missing-point",
    "coverage",
  ])("rejects inconsistent %s evidence instead of displaying a plausible result", async (fault) => {
    const body = structuredClone(decision);
    if (fault === "release") body.context.release_id = "b".repeat(64);
    if (fault === "cutoff") body.context.cutoff_local = "09:45";
    if (fault === "publication")
      body.analysis.points[0].forecast.publication_utc = "2026-01-31T09:00:01Z";
    if (fault === "download") body.export_url = "https://example.test/export.csv";
    if (fault === "future-actual")
      Object.assign(body.analysis.points[0], { actual: { generation_mw: 5 } });
    if (fault === "missing-point") body.analysis.points.pop();
    if (fault === "coverage") body.analysis.coverage.missing = 1;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(apiResponse(body)));
    await expect(loadDecision(filters)).rejects.toMatchObject({ code: "UNSUPPORTED_CONTRACT" });
  });
  it("rejects a response header that belongs to another context", async () => {
    const response = apiResponse(decision);
    response.headers.set("X-Analysis-Context-ID", "b".repeat(64));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
    await expect(loadDecision(filters)).rejects.toBeInstanceOf(ServiceError);
  });
  it("propagates the request reference and safe server explanation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        apiResponse(
          {
            code: "DATABASE_UNAVAILABLE",
            message: "Stored source data is unavailable.",
            request_id: "safe-reference",
          },
          503,
        ),
      ),
    );
    await expect(loadDecision(filters)).rejects.toMatchObject({
      code: "DATABASE_UNAVAILABLE",
      requestId: "safe-reference",
      status: 503,
    });
  });
  it("rejects unsupported retrospective policies and unsafe provenance links", async () => {
    const body = structuredClone(accuracy);
    body.context.comparison_policy = "unverified_policy";
    const fetch = vi.fn().mockResolvedValueOnce(apiResponse(body));
    vi.stubGlobal("fetch", fetch);
    await expect(loadAccuracy({ ...filters, to: "2026-01-01" })).rejects.toBeInstanceOf(
      ServiceError,
    );
    const source = structuredClone(quality);
    source.raw_batches[0].source_url = "javascript:alert(1)";
    fetch.mockResolvedValueOnce(apiResponse(source));
    await expect(loadQuality(filters.release)).rejects.toBeInstanceOf(ServiceError);
  });
  it("verifies CSV media type, release, and context before exposing a download", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(apiResponse(decision));
    vi.stubGlobal("fetch", fetch);
    const result = await loadDecision(filters);
    fetch.mockResolvedValueOnce(
      new Response("error_mw\r\n-3553\r\n", {
        headers: {
          "Content-Type": "text/csv",
          "X-Analysis-Context-ID": result.analysis_context_id,
          "X-Dataset-Release": filters.release,
          "Content-Disposition": 'attachment; filename="winddesk-decision.csv"',
        },
      }),
    );
    const download = await downloadCsv(result);
    expect(download.filename).toBe("winddesk-decision.csv");
    expect(await download.blob.text()).toContain("-3553");
    fetch.mockResolvedValueOnce(
      new Response("wrong", {
        headers: {
          "Content-Type": "text/csv",
          "X-Analysis-Context-ID": "b".repeat(64),
          "X-Dataset-Release": filters.release,
        },
      }),
    );
    await expect(downloadCsv(result)).rejects.toMatchObject({ code: "DOWNLOAD_CONTEXT_MISMATCH" });
    fetch.mockResolvedValueOnce(
      apiResponse(
        {
          code: "ANALYSIS_CONTEXT_MISMATCH",
          message: "Refresh the analysis before downloading.",
          request_id: "download-reference",
        },
        409,
      ),
    );
    await expect(downloadCsv(result)).rejects.toMatchObject({
      code: "ANALYSIS_CONTEXT_MISMATCH",
      status: 409,
    });
  });
});
