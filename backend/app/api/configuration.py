"""Expose non-secret pilot configuration to the frontend."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from backend.app.api.dataset import get_dataset_state
from backend.app.domain.policy import PILOT_POLICY, PilotPolicy
from backend.app.ingestion.archive import ATTRIBUTION, LICENCE_URL
from backend.app.persistence.releases import DatasetState

router = APIRouter(prefix="/api/v1", tags=["configuration"])


class DatasetStatus(BaseModel):
    status: Literal["not_initialized", "available", "unavailable"] = "not_initialized"
    release_id: str | None = None
    forecast_versions: int = 0
    actual_versions: int = 0
    quality_status: str | None = None
    code: str = "NO_ACCEPTED_DATASET"


class ConfigurationResponse(BaseModel):
    application: str = "Wind Desk"
    version: str = "0.1.0"
    stage: Literal["foundation", "data_ready"] = "foundation"
    policy: PilotPolicy
    default_cutoff_local: str
    dataset: DatasetStatus
    build_sha: str
    data_attribution: str = ATTRIBUTION
    data_licence_url: str = LICENCE_URL
    supported_comparison_policies: tuple[Literal["source_timestamp_v1"], ...] = (
        "source_timestamp_v1",
    )
    selection_policy: Literal["latest_source_key_v1"] = "latest_source_key_v1"
    metrics_version: Literal["metrics_v1"] = "metrics_v1"
    analysis_context_version: Literal["analysis_context_v1"] = "analysis_context_v1"


@router.get("/config", response_model=ConfigurationResponse)
def configuration(
    request: Request, state: Annotated[DatasetState, Depends(get_dataset_state)]
) -> ConfigurationResponse:
    settings = request.app.state.settings
    release = state.release
    quality = release["quality"] if release else {}
    return ConfigurationResponse(
        stage="data_ready" if release else "foundation",
        policy=PILOT_POLICY,
        default_cutoff_local=settings.default_cutoff_local.isoformat(timespec="minutes"),
        dataset=DatasetStatus(
            status="available"
            if release
            else ("not_initialized" if state.database else "unavailable"),
            release_id=release["id"] if release else None,
            forecast_versions=quality.get("forecast_versions", 0),
            actual_versions=quality.get("actual_versions", 0),
            quality_status=quality.get("status"),
            code=state.code,
        ),
        build_sha=settings.build_sha,
    )
