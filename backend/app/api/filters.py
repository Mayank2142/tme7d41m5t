"""Bounded public query contracts; reject ambiguity before any source reads."""

import re
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import Request
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from backend.app.domain.calendar import parse_cutoff
from backend.app.domain.policy import PILOT_POLICY
from backend.app.errors import ApiProblem

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ComparisonPolicy = Literal["source_timestamp_v1"]


def _calendar_date(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        result = value
    else:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Use a calendar date in YYYY-MM-DD format")
        result = date.fromisoformat(value)
    if not PILOT_POLICY.decision_from <= result <= PILOT_POLICY.decision_to:
        raise ValueError("Purchase decision dates must be within January 2026")
    return result


def _cutoff(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Cutoff must use local HH:MM format")
    return parse_cutoff(value).isoformat(timespec="minutes")


DecisionDate = Annotated[date, BeforeValidator(_calendar_date)]
Cutoff = Annotated[str, BeforeValidator(_cutoff)]


class ReleaseFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    release_id: Sha256 | None = None


class DecisionFilters(ReleaseFilters):
    decision_date: DecisionDate
    cutoff_local: Cutoff | None = None


class AccuracyFilters(ReleaseFilters):
    decision_from: DecisionDate
    decision_to: DecisionDate
    cutoff_local: Cutoff | None = None
    comparison_policy: ComparisonPolicy = "source_timestamp_v1"

    @model_validator(mode="after")
    def ordered_range(self):
        if self.decision_to < self.decision_from:
            raise ValueError("decision_to must be on or after decision_from")
        return self


class ExportFilters(ReleaseFilters):
    mode: Literal["decision", "accuracy"]
    decision_date: DecisionDate | None = None
    decision_from: DecisionDate | None = None
    decision_to: DecisionDate | None = None
    cutoff_local: Cutoff | None = None
    comparison_policy: ComparisonPolicy | None = None
    expected_context_id: Sha256 | None = None

    @model_validator(mode="after")
    def mode_filters(self):
        if self.mode == "decision":
            if self.decision_date is None:
                raise ValueError("Decision export requires decision_date")
            if any(
                item is not None
                for item in (self.decision_from, self.decision_to, self.comparison_policy)
            ):
                raise ValueError("Decision export does not accept accuracy filters")
        else:
            if self.decision_from is None or self.decision_to is None:
                raise ValueError("Accuracy export requires decision_from and decision_to")
            if self.decision_date is not None:
                raise ValueError("Accuracy export does not accept decision_date")
            if self.decision_to < self.decision_from:
                raise ValueError("decision_to must be on or after decision_from")
        return self


def reject_duplicate_filters(request: Request) -> None:
    keys = [key for key, _ in request.query_params.multi_items()]
    if len(keys) != len(set(keys)):
        raise ApiProblem(422, "DUPLICATE_FILTER", "Supply each query parameter only once.")
