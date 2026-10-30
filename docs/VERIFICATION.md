# Verification and release gates

Run checks against the bundled January release. Tests and normal CI never call Elexon. Dependency installation and container pulls still require access to their package registries. An explicit operator backfill is the only way to fetch a new source vintage.

## Required commands

Use Python 3.12, uv 0.13.6, Node 24, npm, Git, and a working Docker Linux engine. Install dependencies with `uv sync --frozen` and `npm ci --prefix frontend`. Configure `GRID_TEST_DATABASE_URL` for a dedicated PostgreSQL database whose role can create test schemas.

```text
uv lock --check
uv run --frozen python scripts/check_repository.py
uv run --frozen ruff check backend scripts
uv run --frozen ruff format --check backend scripts
uv run --frozen pytest --junitxml=output/pytest.xml
npm run lint --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend
uv build --wheel --out-dir output/dist
uv run --frozen python scripts/verify_wheel.py output/dist/wind_desk-0.1.0-py3-none-any.whl
```

PostgreSQL tests are explicitly skipped without their database variable. A release check must have no such skips. The suite uses random schemas and removes only those schemas. Never supply a production database.

## Running-service and browser gates

Start the seeded API and built frontend on one origin, then run:

```text
uv run --frozen python scripts/verify_service.py --base-url http://127.0.0.1:8000 --output output/service.json
cd frontend
npx playwright install chromium
npm run test:browser
```

`verify_service.py` checks readiness, the accepted real release, January boundaries, cutoff eligibility, canonical context hashes, CSV/JSON identity, all 1,488 half-hour CSV rows at each of two cutoffs, and independently recomputes all four metrics using Python's standard statistics library. It also checks provenance, safe errors, read-only routes, asset caching, and browser security headers. Its stable fingerprint excludes request identifiers and supports a before/after restart comparison. It expects the exact bundled release; a new data vintage requires a deliberate acceptance update.

The standalone [Playwright library](https://playwright.dev/docs/library) runner follows the actual Decision → cutoff draft/apply → CSV → Accuracy → daily drill-down → Methodology → reload journey. It checks chart keyboard controls, displayed metrics, cross-view state, exact downloaded bytes, 1440/390/320-pixel layouts, and console errors. Browser network requests outside the selected origin fail the check. This is a focused workflow gate, not a comprehensive accessibility or performance audit.

The isolated browser context explicitly grants clipboard permissions to the selected origin for successful-copy checks and reads back the exact copied analysis ID. It does not change permissions in a user's normal browser. The reference component tests separately cover permission denial and the manual-copy fallback.

Set `GRID_BROWSER_BASE_URL` to another running origin and `GRID_BROWSER_OUTPUT` to an evidence directory. On a prepared Windows machine with Chrome, set `$env:GRID_BROWSER_CHANNEL='chrome'`; CI uses pinned Playwright Chromium. Browser output includes screenshots, download hashes and a JSON report; failures retain a trace. Generated artifacts are ignored by Git.

## Container gate

```text
uv run --frozen python scripts/verify_containers.py --project winddesk-phase6
```

The command refuses an existing Compose project. It builds the pinned multi-stage image, starts a new PostgreSQL volume, waits for migration/seed and web health, verifies non-root/read-only/capability restrictions and the build label, runs both service and browser gates, replays initialization, restarts PostgreSQL and the web process, and compares stable results. Logs and evidence go under `output/containers`. Finally it removes only that newly owned project's containers, network and volumes. Downloading dependencies and images may take several minutes.

The test uses ports 18000 and 15432 by default, leaving native development ports available. Override `GRID_HTTP_PORT` and `GRID_POSTGRES_PORT` for conflicts. Set `GRID_BUILD_SHA` to the source revision; it becomes both an OCI label and analysis context input. Local Compose deliberately uses development credentials and environment; hosted deployments must supply separate credentials, a restricted application role, TLS and the production environment.

All base images use verified registry manifest digests; [container metadata](research/container-images.json) records their sources. The runtime contains the locked backend, built static frontend and attributed seed, runs as `app`, and supports a read-only filesystem with temporary scratch space. `seed` reads its bundled inputs without rewriting the manifest; `seed --report output/report.json` is an explicit operator write.

## CI and publication checks

[The workflow](../.github/workflows/ci.yml) uses read-only repository permissions, immutable Action references, no persisted checkout credentials, bounded jobs, and superseded-run cancellation. The quality job includes real PostgreSQL integration tests. The dependent container job builds and exercises the same image and stores seven-day artifacts, including failures. It performs no deployment, image push or source backfill and needs no account secrets. See [verified Action metadata](research/ci-actions.json).

`check_repository.py` examines tracked and non-ignored untracked publication inputs, rejects local/private artifacts and recognizes several high-confidence credential formats without printing their values. It supplements human review and the eventual GitHub secret scanner; it is not a proof that arbitrary secrets cannot exist. Lockfiles are committed; exact Playwright and the pinned wheel build backend are included. Update dependencies and base digests deliberately, then rerun the gates.

Workflow validation and local tests are recorded separately from a real GitHub Actions run. The [public repository](https://github.com/Mayank2142/tme7d41m5t) is published; [the full Linux run](https://github.com/Mayank2142/tme7d41m5t/actions/runs/41096413755) passed quality and container jobs. [Phase 8 evidence](PHASE_8_STATUS.md) records the commit, artifacts, test counts and persistence result. The Actions page/badge reports subsequent runs independently. Phase 6 used an explicitly labeled clean source copy; the subsequent [local-readiness record](LOCAL_READINESS.md) tracks verification from an actual committed Git clone.

## Public request protection

API and health responses are not cached. HTML revalidates; successful built assets are immutable, and missing assets are not cached. Responses include nosniff, frame denial, a restrictive referrer policy, permissions restrictions and CSP. The application permits its own scripts; inline style attributes support its SVG charts and daily bars. Only Swagger documentation has a scoped external-script/inline-script exception. Production HTTPS responses add HSTS.

`GRID_API_RATE_LIMIT_ENABLED=true` and `GRID_API_RATE_LIMIT_PER_MINUTE=120` enable a bounded sliding-window backstop per direct peer, per process. Liveness is exempt; readiness shares the API quota/admission limits. Responses use safe JSON, a request reference and `Retry-After` when limited. The application does not read caller-supplied forwarding headers for its quota. Configure trusted proxy identity and a shared ingress quota before operational scaling; individual serverless instances cannot provide a global quota. [Phase 7](PHASE_7_STATUS.md) records the public HTTPS and free edge rules already verified. This pilot remains a public read-only historical analysis, without operational identity/access controls or a procurement execution API.
