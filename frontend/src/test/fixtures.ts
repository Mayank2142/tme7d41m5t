import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";
import { gunzipSync } from "node:zlib";
import accuracy from "./fixtures/accuracy.json";
import configuration from "./fixtures/configuration.json";
import decision from "./fixtures/decision.json";
import january1 from "./fixtures/decision-january-1.json";
import later from "./fixtures/decision-later.json";
import quality from "./fixtures/quality.json";

export { accuracy, configuration, decision, january1, later, quality };
export const month = JSON.parse(
  gunzipSync(
    readFileSync(new NodeURL("./fixtures/accuracy-month.json.gz", import.meta.url)),
  ).toString("utf8"),
) as typeof accuracy;
export const filters = {
  date: "2026-01-31",
  from: "2026-01-01",
  to: "2026-01-31",
  cutoff: "09:00",
  release: decision.context.release_id,
};
export function apiResponse(value: unknown, status = 200): Response {
  const body = value as { analysis_context_id?: string; context?: { release_id: string } };
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      "Content-Type": "application/json",
      "X-Analysis-Context-ID": body.analysis_context_id ?? "",
      "X-Dataset-Release": body.context?.release_id ?? "",
      "X-Request-ID": "test-request",
    },
  });
}
