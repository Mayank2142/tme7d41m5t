"""Process liveness is distinct from PostgreSQL and accepted-release readiness."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.app.api.dataset import get_dataset_state
from backend.app.persistence.releases import DatasetState

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "wind-desk-api"}


@router.get("/ready", responses={503: {"description": "Database or dataset is not ready"}})
def readiness(state: Annotated[DatasetState, Depends(get_dataset_state)]) -> JSONResponse:
    ready = state.code == "OK"
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "database": "available" if state.database else "unavailable",
            "dataset": "available" if state.release else "not_initialized",
            "release_id": state.release["id"] if state.release else None,
            "code": state.code,
        },
    )
