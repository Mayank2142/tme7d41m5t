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
from backend.app.services.cached_analysis import AnalysisPayload, cached_analysis

ERROR_RESPONSES = {
    status: {"model": ErrorResponse} for status in (400, 403, 404, 409, 422, 429, 500, 503)
}
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


def _record_context(request: Request, result: AnalysisPayload) -> None:
    request.state.analysis_context_id = result.context_id
    request.state.release_id = result.release_id


def _analysis(request, reader, mode, start, end, cutoff, release_id):
    result = cached_analysis(
        request.app.state.response_cache,
        reader,
        mode,
        start,
        end,
        cutoff,
        release_id,
        request.app.state.settings.build_sha,
    )
    _record_context(request, result)
    return result


@router.get("/decision-view", response_model=DecisionResponse)
def decision_view(
    request: Request,
    filters: Annotated[DecisionFilters, Query()],
    reader: Reader,
) -> Response:
    result = _analysis(
        request,
        reader,
        "decision",
        filters.decision_date,
        filters.decision_date,
        _cutoff(request, filters.cutoff_local),
        filters.release_id,
    )
    return Response(result.json, media_type="application/json", headers=result.headers)


@router.get("/accuracy", response_model=AccuracyResponse)
def accuracy(
    request: Request,
    filters: Annotated[AccuracyFilters, Query()],
    reader: Reader,
) -> Response:
    result = _analysis(
        request,
        reader,
        "accuracy",
        filters.decision_from,
        filters.decision_to,
        _cutoff(request, filters.cutoff_local),
        filters.release_id,
    )
    return Response(result.json, media_type="application/json", headers=result.headers)


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
    if filters.mode == "decision":
        start = end = filters.decision_date
    else:
        start, end = filters.decision_from, filters.decision_to
    result = _analysis(request, reader, filters.mode, start, end, cutoff, filters.release_id)
    if filters.expected_context_id and not compare_digest(
        filters.expected_context_id, result.context_id
    ):
        raise ApiProblem(
            409,
            "ANALYSIS_CONTEXT_MISMATCH",
            "The analysis context changed. Refresh the analysis before downloading.",
        )
    return Response(
        content=result.csv,
        media_type="text/csv",
        headers=result.headers
        | {"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
