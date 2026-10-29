"""Thin public read controllers over the same analysis service used by CSV."""

from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from backend.app.api.dataset import get_dataset_reader
from backend.app.api.filters import (
    AccuracyFilters,
    DecisionFilters,
    ExportFilters,
    reject_duplicate_filters,
)
from backend.app.contracts import AccuracyResponse, DecisionResponse, ErrorResponse
from backend.app.domain.calendar import parse_cutoff
from backend.app.errors import ApiProblem
from backend.app.persistence.reader import DatasetReader
from backend.app.services.analysis import accuracy_response, decision_response
from backend.app.services.csv_export import render_csv

ERROR_RESPONSES = {status: {"model": ErrorResponse} for status in (404, 409, 422, 500, 503)}
router = APIRouter(
    prefix="/api/v1",
    tags=["analysis"],
    dependencies=[Depends(reject_duplicate_filters)],
    responses=ERROR_RESPONSES,
)
Reader = Annotated[DatasetReader, Depends(get_dataset_reader)]


def _cutoff(request: Request, supplied: str | None):
    return (
        parse_cutoff(supplied)
        if supplied is not None
        else request.app.state.settings.default_cutoff_local
    )


def _headers(result) -> dict[str, str]:
    return {
        "X-Analysis-Context-ID": result.analysis_context_id,
        "X-Dataset-Release": result.context.release_id,
    }


def _record_context(request: Request, result) -> None:
    request.state.analysis_context_id = result.analysis_context_id
    request.state.release_id = result.context.release_id


@router.get("/decision-view", response_model=DecisionResponse)
def decision_view(
    request: Request,
    response: Response,
    filters: Annotated[DecisionFilters, Query()],
    reader: Reader,
) -> DecisionResponse:
    result = decision_response(
        reader,
        filters.decision_date,
        _cutoff(request, filters.cutoff_local),
        filters.release_id,
        request.app.state.settings.build_sha,
    )
    _record_context(request, result)
    response.headers.update(_headers(result))
    return result


@router.get("/accuracy", response_model=AccuracyResponse)
def accuracy(
    request: Request,
    response: Response,
    filters: Annotated[AccuracyFilters, Query()],
    reader: Reader,
) -> AccuracyResponse:
    result = accuracy_response(
        reader,
        filters.decision_from,
        filters.decision_to,
        _cutoff(request, filters.cutoff_local),
        filters.release_id,
        request.app.state.settings.build_sha,
    )
    _record_context(request, result)
    response.headers.update(_headers(result))
    return result


@router.get(
    "/export.csv",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}, "description": "UTF-8 CSV with source lineage"}},
)
def export_csv(
    request: Request,
    filters: Annotated[ExportFilters, Query()],
    reader: Reader,
) -> Response:
    cutoff = _cutoff(request, filters.cutoff_local)
    build = request.app.state.settings.build_sha
    if filters.mode == "decision":
        result = decision_response(reader, filters.decision_date, cutoff, filters.release_id, build)
    else:
        result = accuracy_response(
            reader, filters.decision_from, filters.decision_to, cutoff, filters.release_id, build
        )
    _record_context(request, result)
    if filters.expected_context_id and not compare_digest(
        filters.expected_context_id, result.analysis_context_id
    ):
        raise ApiProblem(
            409,
            "ANALYSIS_CONTEXT_MISMATCH",
            "The analysis context changed. Refresh the analysis before downloading.",
        )
    filename = (
        f"winddesk-{result.context.mode}-{result.context.decision_from.isoformat()}-"
        f"{result.context.decision_to.isoformat()}-{result.analysis_context_id[:12]}.csv"
    )
    return Response(
        content=render_csv(result),
        media_type="text/csv",
        headers=_headers(result) | {"Content-Disposition": f'attachment; filename="{filename}"'},
    )
