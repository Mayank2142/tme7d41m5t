"""Expose accepted coverage evidence without raw payloads or credentials."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.api.dataset import get_dataset_reader
from backend.app.api.filters import ReleaseFilters, reject_duplicate_filters
from backend.app.contracts import DataQualityResponse, ErrorResponse
from backend.app.persistence.reader import DatasetReader

router = APIRouter(
    prefix="/api/v1",
    tags=["data quality"],
    dependencies=[Depends(reject_duplicate_filters)],
    responses={status: {"model": ErrorResponse} for status in (404, 422, 503)},
)


@router.get("/data-quality", response_model=DataQualityResponse)
def data_quality(
    filters: Annotated[ReleaseFilters, Query()],
    reader: Annotated[DatasetReader, Depends(get_dataset_reader)],
) -> DataQualityResponse:
    release = reader.release(filters.release_id)
    return DataQualityResponse(
        release_id=release["id"],
        created_at=release["created_at"],
        quality=release["quality"],
        raw_batches=reader.provenance(release["id"]),
    )
