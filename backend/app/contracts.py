"""Typed read responses shared by JSON services and CSV serialization."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.analysis import AccuracyAnalysis, DecisionAnalysis
from backend.app.ingestion.archive import ATTRIBUTION, LICENCE_URL

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Count = Annotated[int, Field(ge=0)]


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DecisionContext(Contract):
    context_version: Literal["analysis_context_v1"] = "analysis_context_v1"
    mode: Literal["decision"] = "decision"
    release_id: Sha256
    source_parser: str
    application_version: Literal["0.1.0"] = "0.1.0"
    build_sha: str
    decision_from: date
    decision_to: date
    cutoff_local: str
    timezone: Literal["Europe/London"] = "Europe/London"
    calendar_policy: Literal["january_decisions_v1"] = "january_decisions_v1"
    selection_policy: Literal["latest_source_key_v1"] = "latest_source_key_v1"
    availability_model: Literal["source_publication_time"] = "source_publication_time"
    forecast_cadence_minutes: Literal[60] = 60


class AccuracyContext(DecisionContext):
    mode: Literal["accuracy"] = "accuracy"
    comparison_policy: Literal["source_timestamp_v1"] = "source_timestamp_v1"
    actual_vintage_policy: Literal["latest_publication_in_release_v1"] = (
        "latest_publication_in_release_v1"
    )
    metrics_version: Literal["metrics_v1"] = "metrics_v1"
    actual_interval_minutes: Literal[30] = 30


class DecisionSource(Contract):
    forecast_dataset: Literal["WINDFOR"] = "WINDFOR"
    forecast_endpoint: str = "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream"
    data_quality_url: str
    attribution: str = ATTRIBUTION
    licence_url: str = LICENCE_URL


class AccuracySource(DecisionSource):
    actual_dataset: Literal["FUELHH_WIND"] = "FUELHH_WIND"
    actual_endpoint: str = (
        "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?fuelType=WIND"
    )


class DecisionResponse(Contract):
    analysis_context_id: Sha256
    context: DecisionContext
    analysis: DecisionAnalysis
    source: DecisionSource
    export_url: str


class AccuracyResponse(Contract):
    analysis_context_id: Sha256
    context: AccuracyContext
    analysis: AccuracyAnalysis
    source: AccuracySource
    export_url: str


class QualityIssue(Contract):
    target: datetime
    reason: str


class CutoffQuality(Contract):
    expected: Count
    valid: Count
    issues: list[QualityIssue]


class DecisionQuality(Contract):
    decision_date: date
    delivery_date: date
    actual_expected: Count
    actual_valid: Count
    actual_issues: list[QualityIssue]
    forecast_cutoffs: dict[str, CutoffQuality]


class ReleaseQuality(Contract):
    normalized_versions_sha256: Sha256 | None = None
    acceptance_policy: str
    validation_version: str
    parser_version: str
    status: Literal["complete", "partial"]
    forecast_versions: Count
    actual_versions: Count
    exact_duplicate_rows: Count
    conflicting_source_keys: Count
    invalid_source_versions: Count
    expected_actual_half_hours: Count
    valid_actual_half_hours: Count
    expected_forecast_targets_per_cutoff: Count
    valid_forecast_targets_by_cutoff: dict[str, Count]
    decisions: list[DecisionQuality]


class RawProvenance(Contract):
    id: Sha256
    dataset: Literal["WINDFOR", "FUELHH"]
    source_url: str
    payload_sha256: Sha256
    received_at: datetime


class DataQualityResponse(Contract):
    release_id: Sha256
    created_at: datetime
    attribution: str = ATTRIBUTION
    licence_url: str = LICENCE_URL
    quality: ReleaseQuality
    raw_batches: list[RawProvenance]


class FieldProblem(Contract):
    field: str
    code: str
    message: str


class ErrorResponse(Contract):
    code: str
    message: str
    request_id: str
    errors: list[FieldProblem] = Field(default_factory=list)
