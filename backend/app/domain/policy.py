"""Fixed assignment scope, shared by the configuration API and later analysis."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PilotPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_version: Literal["january_decisions_v1"] = "january_decisions_v1"
    timezone: Literal["Europe/London"] = "Europe/London"
    decision_from: date = date(2026, 1, 1)
    decision_to: date = date(2026, 1, 31)
    delivery_from: date = date(2026, 1, 2)
    delivery_to: date = date(2026, 2, 1)
    comparison_policy: Literal["source_timestamp_v1"] = "source_timestamp_v1"
    availability_model: Literal["source_publication_time"] = "source_publication_time"
    forecast_cadence_minutes: Literal[60] = 60
    actual_interval_minutes: Literal[30] = 30
    cutoff_is_illustrative: Literal[True] = True


PILOT_POLICY = PilotPolicy()
