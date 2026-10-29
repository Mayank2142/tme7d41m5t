import { CUTOFF, type Filters, SHA } from "../state";
import type { AccuracyResponse, DecisionResponse, QualityResponse } from "./types";

export class ServiceError extends Error {
  constructor(
    message: string,
    public code = "SERVICE_ERROR",
    public requestId: string | null = null,
    public status = 0,
  ) {
    super(message);
  }
}
function require(value: unknown): asserts value {
  if (!value)
    throw new ServiceError(
      "The service returned an unsupported analysis contract. Reload the analysis or contact the operator.",
      "UNSUPPORTED_CONTRACT",
    );
}
function obj(value: unknown): Record<string, unknown> {
  require(value && typeof value === "object" && !Array.isArray(value));
  return value as Record<string, unknown>;
}
function array(value: unknown): unknown[] {
  require(Array.isArray(value));
  return value;
}
const count = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const finite = (value: unknown) =>
  value === null || (typeof value === "number" && Number.isFinite(value));
const instant = (value: unknown): value is string =>
  typeof value === "string" && value.endsWith("Z") && Number.isFinite(Date.parse(value));
const hash = (value: unknown): value is string => typeof value === "string" && SHA.test(value);
function source(value: unknown) {
  const item = obj(value);
  require(["valid", "invalid", "missing"].includes(String(item.state)));
  const ids = array(item.source_version_ids);
  require(ids.every(hash));
  require(
    item.state === "valid"
      ? count(item.generation_mw) && item.reason === null
      : item.generation_mw === null && typeof item.reason === "string",
  );
  require(
    item.state === "missing"
      ? item.publication_utc === null && ids.length === 0
      : instant(item.publication_utc) && ids.length > 0,
  );
  return item;
}
function coverage(value: unknown, ledger = false) {
  const item = obj(value);
  const fields = ledger
    ? ["forecast_missing", "forecast_invalid", "actual_missing", "actual_invalid", "paired"]
    : ["valid", "missing", "invalid"];
  require(count(item.expected) && fields.every((key) => count(item[key])));
  require(fields.reduce((total, key) => total + Number(item[key]), 0) === item.expected);
  const percentage = item[ledger ? "paired_percent" : "valid_percent"];
  require(
    finite(percentage) &&
      (item.expected > 0
        ? typeof percentage === "number" && percentage >= 0 && percentage <= 100
        : percentage === null),
  );
  return item;
}
function metrics(value: unknown, paired: unknown) {
  const item = obj(value);
  require(item.version === "metrics_v1" && item.unit === "MW" && item.paired_targets === paired);
  for (const key of ["mae_mw", "rmse_mw", "bias_mw", "p90_absolute_error_mw"]) {
    require(
      finite(item[key]) && (paired === 0 ? item[key] === null : typeof item[key] === "number"),
    );
  }
  require(paired === 0 ? item.reason === "NO_VALID_PAIRS" : item.reason === null);
}
function windowFields(value: unknown, day: string, cutoff: string) {
  const item = obj(value);
  require(
    item.decision_date === day && item.cutoff_local === cutoff && item.timezone === "Europe/London",
  );
  require(
    instant(item.cutoff_utc) && instant(item.delivery_start_utc) && instant(item.delivery_end_utc),
  );
  const delivery = new Date(`${day}T00:00:00Z`);
  delivery.setUTCDate(delivery.getUTCDate() + 1);
  require(
    item.delivery_date === delivery.toISOString().slice(0, 10) &&
      item.delivery_start_utc === delivery.toISOString().replace(".000Z", "Z"),
  );
  require(Date.parse(item.delivery_end_utc) - Date.parse(item.delivery_start_utc) === 86_400_000);
  require(item.cutoff_utc === `${day}T${cutoff}:00Z`);
  return item;
}
function target(value: unknown, window: Record<string, unknown>, index: number, interval: number) {
  require(
    instant(value) &&
      Date.parse(value) ===
        Date.parse(String(window.delivery_start_utc)) + index * interval * 60_000,
  );
}
function localUrl(value: unknown, pathname: string) {
  require(typeof value === "string" && value.startsWith(`${pathname}?`));
  const url = new URL(value, "http://workbench.local");
  require(url.origin === "http://workbench.local" && url.pathname === pathname);
  for (const key of url.searchParams.keys()) require(url.searchParams.getAll(key).length === 1);
  return url;
}
function envelope(value: unknown, mode: "decision" | "accuracy", filters: Filters) {
  const body = obj(value);
  const context = obj(body.context);
  const metadata = obj(body.source);
  require(
    hash(body.analysis_context_id) &&
      context.release_id === filters.release &&
      context.mode === mode,
  );
  require(
    context.context_version === "analysis_context_v1" &&
      context.timezone === "Europe/London" &&
      context.calendar_policy === "january_decisions_v1",
  );
  require(
    context.selection_policy === "latest_source_key_v1" &&
      context.availability_model === "source_publication_time" &&
      context.forecast_cadence_minutes === 60,
  );
  require(
    context.cutoff_local === filters.cutoff &&
      typeof context.build_sha === "string" &&
      typeof context.source_parser === "string",
  );
  require(
    context.decision_from === (mode === "decision" ? filters.date : filters.from) &&
      context.decision_to === (mode === "decision" ? filters.date : filters.to),
  );
  require(
    metadata.forecast_dataset === "WINDFOR" &&
      metadata.forecast_endpoint ===
        "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream",
  );
  require(
    typeof metadata.attribution === "string" &&
      String(metadata.licence_url).startsWith("https://www.elexon.co.uk/"),
  );
  require(
    localUrl(metadata.data_quality_url, "/api/v1/data-quality").searchParams.get("release_id") ===
      filters.release,
  );
  const link = localUrl(body.export_url, "/api/v1/export.csv").searchParams;
  require(
    link.get("mode") === mode &&
      link.get("release_id") === filters.release &&
      link.get("cutoff_local") === filters.cutoff &&
      link.get("expected_context_id") === body.analysis_context_id,
  );
  if (mode === "decision") {
    require(
      link.get("decision_date") === filters.date &&
        !("actual_vintage_policy" in context) &&
        !("actual_dataset" in metadata),
    );
  } else {
    require(
      link.get("decision_from") === filters.from &&
        link.get("decision_to") === filters.to &&
        link.get("comparison_policy") === "source_timestamp_v1",
    );
    require(
      context.comparison_policy === "source_timestamp_v1" &&
        context.metrics_version === "metrics_v1" &&
        context.actual_interval_minutes === 30 &&
        context.actual_vintage_policy === "latest_publication_in_release_v1",
    );
  }
  return body;
}
async function responseError(response: Response): Promise<ServiceError> {
  let value: Record<string, unknown> = {};
  try {
    value = obj(await response.json());
  } catch {
    /* A proxy can return a non-JSON failure. */
  }
  return new ServiceError(
    typeof value.message === "string"
      ? value.message
      : `The service returned HTTP ${response.status}. Please try again.`,
    typeof value.code === "string" ? value.code : "HTTP_ERROR",
    typeof value.request_id === "string" ? value.request_id : response.headers.get("x-request-id"),
    response.status,
  );
}
async function get(url: string, signal?: AbortSignal) {
  const response = await fetch(url, { signal });
  if (!response.ok) throw await responseError(response);
  return { response, body: (await response.json()) as unknown };
}
function checkHeaders(response: Response, body: Record<string, unknown>, release: string) {
  require(
    response.headers.get("x-analysis-context-id") === body.analysis_context_id &&
      response.headers.get("x-dataset-release") === release,
  );
}
export async function loadDecision(
  filters: Filters,
  signal?: AbortSignal,
): Promise<DecisionResponse> {
  const params = new URLSearchParams({
    decision_date: filters.date,
    cutoff_local: filters.cutoff,
    release_id: filters.release,
  });
  const { response, body: raw } = await get(`/api/v1/decision-view?${params}`, signal);
  const body = envelope(raw, "decision", filters);
  checkHeaders(response, body, filters.release);
  const analysis = obj(body.analysis);
  const window = windowFields(analysis.window, filters.date, filters.cutoff);
  const points = array(analysis.points);
  require(points.length === 24 && !("actual" in analysis) && !("metrics" in analysis));
  points.forEach((value, index) => {
    const point = obj(value);
    target(point.target_start_utc, window, index, 60);
    const selected = source(point.forecast);
    require(
      !("actual" in point) &&
        !(
          (selected.publication_utc as string | null) &&
          Date.parse(String(selected.publication_utc)) > Date.parse(String(window.cutoff_utc))
        ),
    );
    require(
      point.age_at_cutoff_seconds ===
        (selected.publication_utc
          ? (Date.parse(String(window.cutoff_utc)) - Date.parse(String(selected.publication_utc))) /
            1000
          : null),
    );
  });
  require(coverage(analysis.coverage).expected === 24);
  const summary = obj(analysis.summary);
  require(
    [summary.mean_reported_mw, summary.minimum_reported_mw, summary.maximum_reported_mw].every(
      finite,
    ),
  );
  require(
    [summary.earliest_publication_utc, summary.latest_publication_utc].every(
      (value) => value === null || instant(value),
    ),
  );
  return body as unknown as DecisionResponse;
}
export async function loadAccuracy(
  filters: Filters,
  signal?: AbortSignal,
): Promise<AccuracyResponse> {
  const params = new URLSearchParams({
    decision_from: filters.from,
    decision_to: filters.to,
    cutoff_local: filters.cutoff,
    release_id: filters.release,
    comparison_policy: "source_timestamp_v1",
  });
  const { response, body: raw } = await get(`/api/v1/accuracy?${params}`, signal);
  const body = envelope(raw, "accuracy", filters);
  checkHeaders(response, body, filters.release);
  const analysis = obj(body.analysis);
  const days = array(analysis.days);
  const expectedDays = (Date.parse(filters.to) - Date.parse(filters.from)) / 86_400_000 + 1;
  require(
    days.length === expectedDays &&
      analysis.retrospective === true &&
      analysis.comparison_policy === "source_timestamp_v1",
  );
  days.forEach((value, dayIndex) => {
    const day = obj(value);
    const dayDate = new Date(Date.parse(filters.from) + dayIndex * 86_400_000)
      .toISOString()
      .slice(0, 10);
    const window = windowFields(day.window, dayDate, filters.cutoff);
    const points = array(day.points);
    require(points.length === 24);
    points.forEach((value, index) => {
      const point = obj(value);
      target(point.target_start_utc, window, index, 60);
      const forecast = source(point.forecast);
      const actual = source(point.actual);
      require(
        !forecast.publication_utc ||
          Date.parse(String(forecast.publication_utc)) <= Date.parse(String(window.cutoff_utc)),
      );
      const state =
        forecast.state !== "valid"
          ? `forecast_${forecast.state}`
          : actual.state !== "valid"
            ? `actual_${actual.state}`
            : "paired";
      require(
        point.state === state &&
          point.error_mw ===
            (state === "paired"
              ? Number(forecast.generation_mw) - Number(actual.generation_mw)
              : null),
      );
    });
    const observations = array(day.actual_half_hours);
    require(observations.length === 48);
    observations.forEach((value, index) => {
      const point = obj(value);
      target(point.target_start_utc, window, index, 30);
      source(point.actual);
      require(typeof point.used_in_metrics === "boolean");
    });
    require(coverage(day.coverage, true).expected === 24);
    metrics(day.metrics, obj(day.coverage).paired);
    require(coverage(day.actual_source_coverage).expected === 48);
  });
  const ledger = coverage(analysis.coverage, true);
  require(ledger.expected === expectedDays * 24);
  metrics(analysis.metrics, ledger.paired);
  require(coverage(analysis.actual_source_coverage).expected === expectedDays * 48);
  return body as unknown as AccuracyResponse;
}
export async function loadQuality(release: string, signal?: AbortSignal): Promise<QualityResponse> {
  const { body: raw } = await get(`/api/v1/data-quality?release_id=${release}`, signal);
  const body = obj(raw);
  require(body.release_id === release && instant(body.created_at));
  const quality = obj(body.quality);
  require(["complete", "partial"].includes(String(quality.status)));
  for (const key of [
    "forecast_versions",
    "actual_versions",
    "exact_duplicate_rows",
    "conflicting_source_keys",
    "invalid_source_versions",
    "expected_actual_half_hours",
    "valid_actual_half_hours",
    "expected_forecast_targets_per_cutoff",
  ])
    require(count(quality[key]));
  require(
    array(quality.decisions).length === 31 &&
      typeof quality.parser_version === "string" &&
      typeof quality.validation_version === "string" &&
      typeof quality.acceptance_policy === "string",
  );
  for (const item of array(quality.decisions)) {
    const day = obj(item);
    require(
      typeof day.decision_date === "string" &&
        typeof day.delivery_date === "string" &&
        count(day.actual_valid) &&
        count(day.actual_expected),
    );
    for (const [cutoff, item] of Object.entries(obj(day.forecast_cutoffs))) {
      const ledger = obj(item);
      require(CUTOFF.test(cutoff) && count(ledger.valid) && count(ledger.expected));
    }
  }
  require(
    typeof body.attribution === "string" &&
      String(body.licence_url).startsWith("https://www.elexon.co.uk/"),
  );
  require(
    array(body.raw_batches).every((value) => {
      const row = obj(value);
      return (
        hash(row.id) &&
        hash(row.payload_sha256) &&
        instant(row.received_at) &&
        ["WINDFOR", "FUELHH"].includes(String(row.dataset)) &&
        String(row.source_url).startsWith("https://data.elexon.co.uk/bmrs/api/v1/datasets/")
      );
    }),
  );
  return body as unknown as QualityResponse;
}
export async function downloadCsv(
  result: DecisionResponse | AccuracyResponse,
  signal?: AbortSignal,
) {
  const response = await fetch(result.export_url, { signal });
  if (!response.ok) throw await responseError(response);
  if (
    !response.headers.get("content-type")?.startsWith("text/csv") ||
    response.headers.get("x-analysis-context-id") !== result.analysis_context_id ||
    response.headers.get("x-dataset-release") !== result.context.release_id
  )
    throw new ServiceError(
      "The download did not match this analysis. Reload the analysis before trying again.",
      "DOWNLOAD_CONTEXT_MISMATCH",
    );
  const blob = await response.blob();
  const filename =
    /filename="([a-zA-Z0-9.-]+\.csv)"/.exec(
      response.headers.get("content-disposition") ?? "",
    )?.[1] ?? `winddesk-${result.context.mode}.csv`;
  return { blob, filename };
}
