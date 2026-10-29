export interface PilotPolicy {
  policy_version: "january_decisions_v1";
  timezone: "Europe/London";
  decision_from: string;
  decision_to: string;
  delivery_from: string;
  delivery_to: string;
  comparison_policy: "source_timestamp_v1";
  availability_model: "source_publication_time";
  forecast_cadence_minutes: 60;
  actual_interval_minutes: 30;
  cutoff_is_illustrative: true;
}

export interface Configuration {
  application: string;
  version: string;
  stage: "foundation" | "data_ready";
  policy: PilotPolicy;
  default_cutoff_local: string;
  dataset: {
    status: "not_initialized" | "available" | "unavailable";
    release_id: string | null;
    forecast_versions: number;
    actual_versions: number;
    quality_status: "complete" | "partial" | null;
    code: string;
  };
  build_sha: string;
  data_attribution: string;
  data_licence_url: string;
}

export async function loadConfiguration(signal?: AbortSignal): Promise<Configuration> {
  const response = await fetch("/api/v1/config", { signal });
  if (!response.ok) throw new Error(`Configuration service returned HTTP ${response.status}.`);
  const data: Partial<Configuration> | null = await response.json();
  if (
    !data ||
    !["foundation", "data_ready"].includes(data.stage ?? "") ||
    typeof data.application !== "string" ||
    typeof data.version !== "string" ||
    typeof data.build_sha !== "string" ||
    data.policy?.policy_version !== "january_decisions_v1" ||
    data.policy.timezone !== "Europe/London" ||
    data.policy.decision_from !== "2026-01-01" ||
    data.policy.decision_to !== "2026-01-31" ||
    data.policy.delivery_from !== "2026-01-02" ||
    data.policy.delivery_to !== "2026-02-01" ||
    data.policy.comparison_policy !== "source_timestamp_v1" ||
    data.policy.forecast_cadence_minutes !== 60 ||
    data.policy.actual_interval_minutes !== 30 ||
    typeof data.default_cutoff_local !== "string" ||
    !/^([01]\d|2[0-3]):[0-5]\d$/.test(data.default_cutoff_local) ||
    !["not_initialized", "available", "unavailable"].includes(data.dataset?.status ?? "") ||
    !Number.isInteger(data.dataset?.forecast_versions) ||
    !Number.isInteger(data.dataset?.actual_versions) ||
    (data.dataset?.forecast_versions ?? -1) < 0 ||
    (data.dataset?.actual_versions ?? -1) < 0 ||
    typeof data.data_attribution !== "string" ||
    typeof data.data_licence_url !== "string" ||
    !data.data_licence_url.startsWith("https://www.elexon.co.uk/") ||
    (data.dataset?.status === "available" &&
      (data.stage !== "data_ready" ||
        !["complete", "partial"].includes(data.dataset.quality_status ?? ""))) ||
    (data.stage === "data_ready" && data.dataset?.status !== "available") ||
    (data.dataset?.status === "available"
      ? typeof data.dataset.release_id !== "string" ||
        !/^[a-f0-9]{64}$/.test(data.dataset.release_id)
      : data.dataset?.release_id !== null)
  ) {
    throw new Error("The service returned an unsupported configuration contract.");
  }
  return data as Configuration;
}
