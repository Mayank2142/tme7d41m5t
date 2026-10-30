"""One shared source of database/release readiness for public metadata routes."""

from fastapi import Request

from backend.app.persistence.reader import DatasetReader
from backend.app.persistence.releases import DatasetState, dataset_state


def get_dataset_state(request: Request) -> DatasetState:
    return dataset_state(request.app.state.database)


def get_dataset_reader(request: Request) -> DatasetReader:
    return request.app.state.dataset_reader
