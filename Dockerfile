FROM node:24-bookworm-slim@sha256:c86ecead9e55a5210ac1727de38a4ca840bf03dcaf34dc9749addbf383b1920c AS frontend
WORKDIR /build/frontend
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS backend
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY backend/ backend/
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337 AS runtime
ARG GRID_BUILD_SHA=local
WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
COPY --from=backend /app/.venv /app/.venv
COPY --from=frontend /build/frontend/dist /app/frontend/dist
COPY data/snapshots/ /app/data/snapshots/
ENV PATH="/app/.venv/bin:$PATH" GRID_FRONTEND_DIST=/app/frontend/dist PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 GRID_ENVIRONMENT=production GRID_BUILD_SHA=$GRID_BUILD_SHA
LABEL org.opencontainers.image.title="Wind Desk" org.opencontainers.image.revision=$GRID_BUILD_SHA
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health/live', timeout=3)"]
CMD ["winddesk", "serve", "--host", "0.0.0.0"]
