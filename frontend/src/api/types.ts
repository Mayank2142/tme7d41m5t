export interface Selection {
  state: "valid" | "missing" | "invalid";
  publication_utc: string | null;
  generation_mw: number | null;
  source_version_ids: string[];
  reason: string | null;
}
export interface Window {
  decision_date: string;
  delivery_date: string;
  cutoff_local: string;
  cutoff_utc: string;
  delivery_start_utc: string;
  delivery_end_utc: string;
  timezone: "Europe/London";
}
export interface SourceCoverage {
  expected: number;
  valid: number;
  missing: number;
  invalid: number;
  valid_percent: number | null;
}
export interface Ledger {
  expected: number;
  forecast_missing: number;
  forecast_invalid: number;
  actual_missing: number;
  actual_invalid: number;
  paired: number;
  paired_percent: number | null;
}
export interface Metrics {
  paired_targets: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  p90_absolute_error_mw: number | null;
  reason: string | null;
  version: "metrics_v1";
  unit: "MW";
}
export interface ForecastPoint {
  target_start_utc: string;
  forecast: Selection;
  age_at_cutoff_seconds: number | null;
}
export interface AccuracyPoint {
  target_start_utc: string;
  forecast: Selection;
  actual: Selection;
  state: "forecast_missing" | "forecast_invalid" | "actual_missing" | "actual_invalid" | "paired";
  reason: string | null;
  error_mw: number | null;
}
export interface DecisionAnalysis {
  window: Window;
  points: ForecastPoint[];
  coverage: SourceCoverage;
  summary: {
    mean_reported_mw: number | null;
    minimum_reported_mw: number | null;
    maximum_reported_mw: number | null;
    earliest_publication_utc: string | null;
    latest_publication_utc: string | null;
  };
  selection_policy: "latest_source_key_v1";
  availability_model: "source_publication_time";
}
export interface DailyAccuracy {
  window: Window;
  points: AccuracyPoint[];
  actual_half_hours: { target_start_utc: string; actual: Selection; used_in_metrics: boolean }[];
  metrics: Metrics;
  coverage: Ledger;
  actual_source_coverage: SourceCoverage;
}
export interface AccuracyAnalysis {
  decision_from: string;
  decision_to: string;
  cutoff_local: string;
  days: DailyAccuracy[];
  metrics: Metrics;
  coverage: Ledger;
  actual_source_coverage: SourceCoverage;
  comparison_policy: "source_timestamp_v1";
  selection_policy: "latest_source_key_v1";
  actual_vintage_policy: "latest_publication_in_release_v1";
  availability_model: "source_publication_time";
  retrospective: true;
}
export interface Context {
  context_version: "analysis_context_v1";
  mode: "decision" | "accuracy";
  release_id: string;
  source_parser: string;
  application_version: string;
  build_sha: string;
  decision_from: string;
  decision_to: string;
  cutoff_local: string;
  timezone: "Europe/London";
  calendar_policy: "january_decisions_v1";
  selection_policy: "latest_source_key_v1";
  availability_model: "source_publication_time";
  forecast_cadence_minutes: 60;
  comparison_policy?: "source_timestamp_v1";
  actual_vintage_policy?: "latest_publication_in_release_v1";
  metrics_version?: "metrics_v1";
  actual_interval_minutes?: 30;
}
export interface Source {
  forecast_dataset: "WINDFOR";
  forecast_endpoint: string;
  data_quality_url: string;
  actual_dataset?: "FUELHH_WIND";
  actual_endpoint?: string;
  attribution: string;
  licence_url: string;
}
export interface DecisionResponse {
  analysis_context_id: string;
  context: Context;
  analysis: DecisionAnalysis;
  source: Source;
  export_url: string;
}
export interface AccuracyResponse {
  analysis_context_id: string;
  context: Context;
  analysis: AccuracyAnalysis;
  source: Source;
  export_url: string;
}
export interface QualityResponse {
  release_id: string;
  created_at: string;
  attribution: string;
  licence_url: string;
  quality: {
    status: "complete" | "partial";
    parser_version: string;
    validation_version: string;
    acceptance_policy: string;
    normalized_versions_sha256: string | null;
    forecast_versions: number;
    actual_versions: number;
    exact_duplicate_rows: number;
    conflicting_source_keys: number;
    invalid_source_versions: number;
    expected_actual_half_hours: number;
    valid_actual_half_hours: number;
    expected_forecast_targets_per_cutoff: number;
    valid_forecast_targets_by_cutoff: Record<string, number>;
    decisions: {
      decision_date: string;
      delivery_date: string;
      actual_expected: number;
      actual_valid: number;
      actual_issues: { target: string; reason: string }[];
      forecast_cutoffs: Record<
        string,
        { expected: number; valid: number; issues: { target: string; reason: string }[] }
      >;
    }[];
  };
  raw_batches: {
    id: string;
    dataset: "WINDFOR" | "FUELHH";
    source_url: string;
    payload_sha256: string;
    received_at: string;
  }[];
}
