"""FastAPI factory with shared configuration and a production frontend entry point."""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from backend.app.api.analysis import router as analysis_router
from backend.app.api.configuration import router as configuration_router
from backend.app.api.errors import install_error_handlers
from backend.app.api.health import router as health_router
from backend.app.api.quality import router as quality_router
from backend.app.config import Settings
from backend.app.contracts import ErrorResponse
from backend.app.persistence.database import create_database_engine
from backend.app.security import DOCS_CSP, SECURITY_HEADERS, RequestLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            app.state.database.dispose()

    app = FastAPI(
        title="Wind Desk API",
        version="0.1.0",
        description="Historical GB wind decision support. Versioned source data and validation.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = configured
    # Engine creation is lazy; keep it available on runtimes that do not invoke ASGI lifespan.
    app.state.database = create_database_engine(configured)
    limiter = RequestLimiter(configured.api_rate_limit_per_minute)
    install_error_handlers(app)

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        request.state.request_id = str(uuid4())
        started = perf_counter()
        retry = (
            limiter.retry_after(request.client.host if request.client else "unknown")
            if configured.api_rate_limit_enabled and request.url.path.startswith("/api/v1/")
            else None
        )
        if retry is None:
            response = await call_next(request)
        else:
            request.state.error_code = "RATE_LIMITED"
            response = JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    code="RATE_LIMITED",
                    message="Too many requests. Please retry later.",
                    request_id=request.state.request_id,
                ).model_dump(mode="json"),
                headers={"Retry-After": str(retry)},
            )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers.update(SECURITY_HEADERS)
        if request.url.path == "/api/docs":
            response.headers["Content-Security-Policy"] = DOCS_CSP
        if configured.environment == "production" and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache"
        elif response.status_code == 200 and request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        if request.url.path.startswith(("/api/", "/health/")):
            response.headers["Cache-Control"] = "no-store"
            logging.getLogger("winddesk.api").info(
                json.dumps(
                    {
                        "event": "api_request",
                        "request_id": request.state.request_id,
                        "path": request.url.path,
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
        dist = configured.frontend_dist.resolve()
        target = (dist / path).resolve()
        if not target.is_relative_to(dist):
            raise HTTPException(status_code=404, detail="Not found")
        if path and target.is_file():
            return FileResponse(target)
        if path in {"", "decision", "accuracy", "methodology"} and (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        raise HTTPException(status_code=404, detail="Frontend not built or page not found")

    return app
