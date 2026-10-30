"""FastAPI factory with shared configuration and a production frontend entry point."""

import json
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import PurePosixPath
from threading import BoundedSemaphore
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.gzip import GZipMiddleware

from backend.app.api.analysis import router as analysis_router
from backend.app.api.configuration import router as configuration_router
from backend.app.api.errors import install_error_handlers
from backend.app.api.health import router as health_router
from backend.app.api.quality import router as quality_router
from backend.app.cache import BoundedCache
from backend.app.config import Settings
from backend.app.contracts import ErrorResponse
from backend.app.persistence.database import create_database_engine
from backend.app.persistence.reader import DatasetReader
from backend.app.security import DOCS_CSP, SECURITY_HEADERS, RequestLimiter, request_problem


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            app.state.database.dispose()

    docs = configured.enable_api_docs
    if docs is None:
        docs = configured.environment != "production"
    app = FastAPI(
        title="Wind Desk API",
        version="0.1.0",
        description="Historical GB wind decision support. Versioned source data and validation.",
        docs_url="/api/docs" if docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if docs else None,
        lifespan=lifespan,
    )
    app.state.settings = configured
    # Engine creation is lazy; keep it available on runtimes that do not invoke ASGI lifespan.
    app.state.database = create_database_engine(configured, read_only=True)
    app.state.dataset_reader = DatasetReader(app.state.database, configured.source_cache_mb)
    app.state.response_cache = BoundedCache(
        max_entries=128, max_bytes=configured.response_cache_mb * 1024**2
    )
    limiter = RequestLimiter(configured.api_rate_limit_per_minute)
    admission = BoundedSemaphore(configured.api_max_inflight)
    install_error_handlers(app)
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=4)

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        request.state.request_id = str(uuid4())
        started = perf_counter()
        path = request.scope["path"]
        needs_database = path.startswith("/api/") or path == "/health/ready"
        problem = request_problem(request, configured)
        retry = (
            limiter.retry_after(request.client.host if request.client else "unknown")
            if not problem
            and configured.api_rate_limit_enabled
            and (path.startswith("/api/v1/") or path == "/health/ready")
            else None
        )
        extra_headers = {}
        if retry is not None:
            problem = (429, "RATE_LIMITED", "Too many requests. Please retry later.")
            extra_headers["Retry-After"] = str(retry)
        admitted = False
        if not problem and needs_database:
            admitted = admission.acquire(blocking=False)
            if not admitted:
                problem = (503, "SERVER_BUSY", "The service is busy. Please retry.")
                extra_headers["Retry-After"] = "1"
        if problem:
            status, code, message = problem
            request.state.error_code = code
            response = JSONResponse(
                status_code=status,
                content=ErrorResponse(
                    code=code,
                    message=message,
                    request_id=request.state.request_id,
                ).model_dump(mode="json"),
                headers={"Cache-Control": "no-store", **extra_headers},
            )
        else:
            try:
                response = await call_next(request)
            finally:
                if admitted:
                    admission.release()
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers.update(SECURITY_HEADERS)
        if docs and path == "/api/docs":
            response.headers["Content-Security-Policy"] = DOCS_CSP
        if configured.environment == "production" and request.scope["scheme"] == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache"
        elif response.status_code == 200 and path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        if path.startswith(("/api/", "/health/")):
            response.headers["Cache-Control"] = "no-store"
            logging.getLogger("winddesk.api").info(
                json.dumps(
                    {
                        "event": "api_request",
                        "request_id": request.state.request_id,
                        "path": path[:256],
                        "status": response.status_code,
                        "duration_ms": round((perf_counter() - started) * 1000, 2),
                        "release_id": getattr(request.state, "release_id", None),
                        "analysis_context_id": getattr(request.state, "analysis_context_id", None),
                        "error_code": getattr(request.state, "error_code", None),
                    }
                )
            )
        return response

    app.include_router(configuration_router)
    app.include_router(health_router)
    app.include_router(quality_router)
    app.include_router(analysis_router)

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path == "health" or path.startswith(("api/", "health/")):
            raise HTTPException(status_code=404, detail="Endpoint not found")
        asset = PurePosixPath(path)
        allowed_asset = (
            asset.parts
            and asset.parts[0] == "assets"
            and all(re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", part) for part in asset.parts)
            and asset.suffix.lower() in {".js", ".css", ".svg", ".png", ".webp", ".ico", ".woff2"}
        )
        if not allowed_asset and path not in {"", "decision", "accuracy", "methodology"}:
            raise HTTPException(status_code=404, detail="Not found")
        dist = configured.frontend_dist.resolve()
        target = (dist / (path if allowed_asset else "index.html")).resolve()
        if target.is_relative_to(dist) and target.is_file():
            return FileResponse(target)
        raise HTTPException(status_code=404, detail="Frontend not built or page not found")

    return app
