# Wind Desk

Historical GB wind forecast decision support for January 2026. React and TypeScript frontend, Python FastAPI backend, PostgreSQL, Docker for reproducible local execution, and a verified Vercel deployment.

**Live application: [Wind Desk](https://tme7d41m5t.vercel.app). Phase 7 is complete for the public evaluation pilot.** Decision, Accuracy, and Data & Methodology use the accepted Elexon release in a separate managed PostgreSQL database. Inspect eligible forecasts, publication age, retrospective metrics, coverage, and provenance; share the pinned selection or download matching CSV. The seed contains 19,856 forecast versions and 1,488 WIND actuals. At 09:00, all 744 expected targets pair, with MAE 2,022.47 MW. See [deployment evidence](docs/PHASE_7_STATUS.md), [verification commands](docs/VERIFICATION.md), and the [workbench guide](docs/WORKBENCH.md).

**Public source: [Mayank2142/tme7d41m5t](https://github.com/Mayank2142/tme7d41m5t)** · [GitHub Actions](https://github.com/Mayank2142/tme7d41m5t/actions) · [Recording checklist](docs/RECORDING_CHECKLIST.md).

[![Verify Wind Desk](https://github.com/Mayank2142/tme7d41m5t/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Mayank2142/tme7d41m5t/actions/workflows/ci.yml)

Phase 8 publication is in progress. The user will record the required customer and technical demonstration in their own voice; no video has been published or assignment submitted yet. Do not submit before the unlisted video exists and its playback has been checked.

The [local handoff](docs/LOCAL_READINESS.md) covers the Docker Desktop repair, standard startup helper, committed-checkout verification and remaining external release work. The [demo script](docs/DEMO_SCRIPT.md) prepares the customer and technical recording.

## Local development

Use Python 3.12, Node 24 (recommended), npm, uv, and Docker Desktop with Linux containers.

For application-only startup on Windows, start Docker Desktop and run `.\scripts\local.ps1 -Action Start` from the checkout. It builds the application and checks data readiness. Use `-Action Status` or `-Action Stop` to inspect or stop this project's services; stopping preserves the database volume. See the [local handoff](docs/LOCAL_READINESS.md) for alternate ports and isolated review projects. A working Docker engine is the only runtime prerequisite for this container path.

Copy the development environment file:

```powershell
Copy-Item .env.example .env
```

On macOS/Linux, use `cp .env.example .env`. The checked-in values are local development defaults; use distinct credentials in hosting configuration.

Start PostgreSQL and install the locked Python environment:

```text
docker compose up -d postgres
uv sync --frozen
uv run winddesk check-db
uv run winddesk seed --configure-reader
```

For native serving, switch the web process to the reader login before starting it. In PowerShell, run `$env:GRID_DATABASE_URL = 'postgresql+psycopg://winddesk_reader:winddesk_local@127.0.0.1:5432/winddesk'`, then `uv run winddesk serve --reload`. In bash, use `export GRID_DATABASE_URL='postgresql+psycopg://winddesk_reader:winddesk_local@127.0.0.1:5432/winddesk'`. Keep operator credentials in a separate terminal for later migrations/imports. Docker Compose provisions and separates these logins automatically. All example passwords are development values.

In another terminal:

```text
cd frontend
npm ci
npm run dev
```

Open [the local frontend](http://localhost:5173). Vite proxies `/api` and `/health` to the Python service at port 8000. For a single-origin local preview, run `npm run build` in `frontend`, then run the API from the repository root and open [port 8000](http://localhost:8000).

In the prepared Windows workspace, `.tools\uv.exe` is a local portable uv executable; use it in place of `uv` if uv is not on PATH. After dependencies are installed, the backend can also be started with `.\.venv\Scripts\python.exe -m backend.app.cli serve --reload`. A fresh checkout needs its own uv installation. If PowerShell blocks the npm script shim, use `npm.cmd` instead of `npm`.

The complete container entry point is `docker compose up --build`. Compose waits for PostgreSQL, runs a one-off migration/seed service, and then starts the web service. Seeding is idempotent and uses the bundled archive without an external download. Readiness is 200 only when the database and an accepted release are available. Container startup/image execution still requires a working Docker Linux engine; see the status record for checks actually run.

The prepared Windows workspace now runs the application and PostgreSQL through Docker Desktop 4.97 on ports 8000/5432. Its normal shutdown/restart was verified with unchanged data and results. The earlier portable PostgreSQL 17.11 cluster is retained under `.tools`/`.cache` and is stopped. For optional native development, stop this project's Docker services before using `scripts/local-postgres.ps1 -Action Start`; stop the portable cluster before returning to Docker on the same port. The portable helper does not install or initialize PostgreSQL for a fresh checkout.

## Data operations

| Command | Purpose |
| --- | --- |
| `uv run winddesk migrate` | Apply the checked-in Alembic migrations |
| `uv run winddesk seed` | Migrate and import the bundled January archive, validating before activation |
| `uv run winddesk fetch` | Download missing January request windows into a resumable raw archive |
| `uv run winddesk fetch --refresh` | Re-fetch the source vintage explicitly |
| `uv run winddesk validate --report data/snapshots/manifest.json` | Verify raw checksums, normalize, and report full-window coverage |
| `uv run winddesk backfill --refresh` | Fetch a new source vintage, validate, and import it |
| `uv run winddesk export-release --output output/recovered.json.gz` | Recover the active release's original response payloads from PostgreSQL |
| `uv run winddesk analyze --cutoff 09:00 --output output/analysis-0900.json` | Calculate January accuracy from one accepted release and write every selected point |

The default archive is `data/snapshots/january_2026.json.gz`. `seed` reads the bundled archive and leaves its adjacent manifest unchanged, including on a read-only filesystem. Supply `--report output/report.json` to `seed` or `backfill` for an explicit report write. Existing complete archives are reused unless `--refresh` is requested. Failed downloads leave a `.partial` checkpoint for a later resume. Failed or partial candidates do not replace an accepted release under the default strict policy. `seed --allow-partial` is an explicit operator override that remains labeled partial in metadata; do not use it to hide gaps. Old releases retain their parsed record membership even after the same raw responses are parsed by a new parser version.

`analyze` defaults to all January decision dates and the configured illustrative cutoff. Use `--decision-from 2026-01-31 --decision-to 2026-01-31` for a single decision, or `--release-id` with a full accepted ID to pin a previous release. The summary prints to the terminal; `--output` writes the complete retrospective JSON report. Analysis reads PostgreSQL and does not download fresh source data. See [methodology](docs/METHODOLOGY.md) for selection, actual vintage, coverage, units, and missing-data rules.

## Read endpoints

- `GET /api/v1/config`: non-secret scope, cutoff, policy, version, and dataset status.
- `GET /api/v1/decision-view?decision_date=2026-01-31`: forecast-only replay with coverage, age, provenance, and a pinned export URL.
- `GET /api/v1/accuracy?decision_from=2026-01-01&decision_to=2026-01-31`: retrospective pairs, metrics, daily results, coverage, and original half-hour observations.
- `GET /api/v1/data-quality`: accepted release coverage, request hashes, source URLs, retrieval timestamps, and attribution; accepts an explicit `release_id`.
- `GET /api/v1/export.csv`: requires a `mode` and matching analysis filters; follow the analysis response's `export_url` for the same release and guarded context.
- `GET /health/live`: process liveness, independent of PostgreSQL.
- `GET /health/ready`: database plus accepted-data readiness, with an explicit failure code if either is missing.
- `GET /api/docs`: generated API documentation (local development; disabled by default in production).
- `GET /api/openapi.json`: machine-readable API contract (same documentation setting).

After startup, open [the workbench](http://127.0.0.1:8000/) or [local API docs](http://127.0.0.1:8000/api/docs). The default Decision view covers January 31 with February 1 delivery. Analysis dates are January purchase decisions, cutoff is local `HH:MM`, and the supported comparison is `source_timestamp_v1`. Invalid/ambiguous filters return typed errors; valid missing data returns nulls and coverage. Decision JSON and CSV contain no actuals. Accuracy CSV preserves all 1,488 half-hour targets, marking the 744 native comparison targets and valid metric contributions explicitly. See the [API/export contract](docs/API.md) for context hashing, CSV columns, and errors.

## Checks

```text
uv run ruff check backend scripts
uv run ruff format --check backend scripts
uv run pytest
cd frontend
npm run lint
npm run build
npm test
```

The PostgreSQL integration suite requires `GRID_TEST_DATABASE_URL` pointing to a dedicated development/test database where the test user can create schemas. It creates random isolated schemas and removes them after the tests; never point it at production. On Windows, for the local development database:

```powershell
$env:GRID_TEST_DATABASE_URL = 'postgresql+psycopg://winddesk:winddesk_local@127.0.0.1:5432/winddesk'
uv run pytest
```

Without this variable, PostgreSQL integration checks are explicitly skipped. The latest Phase 7 run passed **107 backend tests with no skips** against local PostgreSQL. The enhanced frontend passed **47 tests**, lint, type checking and the production build. The deployed application passed independent public API/CSV checks and a fresh logged-out Chrome journey at desktop and narrow widths. A replacement deployment retained the same dataset, analysis and export fingerprints. Frontend tests use attributed frozen fixtures. [Phase 7 status](docs/PHASE_7_STATUS.md) records the current evidence; [Phase 6 status](docs/PHASE_6_STATUS.md) retains the earlier baseline.

The subsequent [local-readiness verification](docs/LOCAL_READINESS.md) repeated all 90 backend and 43 frontend tests from a real committed clone, using Docker PostgreSQL and Node 24. It also verified the complete container runner, the standard local helper, database dump/restore into a separate database, and Docker Desktop restart persistence. A clean-checkout pytest temporary-directory bug was found and fixed. The locked Python production dependency audit reported no known advisories across 31 packages; the fresh npm install also reported zero known vulnerabilities.

The [verification guide](docs/VERIFICATION.md) includes the running-service, browser, packaging, publication-input and isolated-container commands. The [CI workflow](.github/workflows/ci.yml) runs quality checks before image, seed, browser and restart gates, without live Elexon calls. Its remote execution requires the later public repository. The request quota is a per-process backstop; a distributed request limit and verified hosting proxy identity remain operational scaling work.

## Concurrency and security

The public dashboard remains read-only. Bounded per-process caches share immutable source indexes and serialized JSON/CSV across requests, with one calculation per concurrent cache key. Rate limits, admission limits, database statement timeouts, explicit host validation, request-size limits, restrictive browser headers and static-file allowlisting reduce common attack paths and resource exhaustion. Docker serves with a separate database login that cannot modify the dataset or select raw response payloads/ingestion records. Production configuration requires explicit hosts, separate database credentials and verified remote PostgreSQL TLS; API documentation defaults off. CI audits both dependency lockfiles.

See [security, measured load results and deployment controls](docs/SECURITY_AND_SCALING.md). The public deployment has HTTPS, automatic DDoS mitigation and two verified free edge deny rules. The web function has only the restricted reader credential, verified PostgreSQL TLS and a one-connection pool; the reader role is capped at 20 connections. Distributed request limits, measured sustained cloud capacity, recovery objectives and independent penetration testing remain operational work. See [hosting controls and limits](docs/PHASE_7_STATUS.md).

The hardening verification passed 102 backend and 43 frontend tests, with no skips in the PostgreSQL-enabled backend run. The local 50-client burst completed 200 requests successfully at about 493 ms p95. The production dependency scans reported zero known advisories at the time of the check. See [the dated evidence](docs/security-scale-evidence.json) for the workload, limits and final container checks.

## Source and analysis policy

Only Elexon WINDFOR and FUELHH WIND records are allowed. January means purchase decision dates, so delivery runs from 2 January through 1 February. The default 09:00 Europe/London cutoff is an illustrative desk assumption. The primary comparison matches source target timestamps; it does not invent half-hour forecasts or assume a full-hour forecast energy profile. The portal describes reported outturn, which may include estimates, rather than final settlement truth.

The real raw-response archive and manifest are bundled under `data/snapshots`. The applicable BMRS open-data licence and attribution were verified during Phase 2; see [data attribution](data/ATTRIBUTION.md). Original bytes and retrieval timestamps are retained independently of normalized values. The older planning research report is separate and is not used as the dataset seed.

## Repository map

| Location | Purpose |
| --- | --- |
| `backend/app/` | Configuration, typed response contracts, API factory, database connection, and CLI |
| `backend/app/api/` | Typed query validation, thin read controllers, and safe error responses |
| `backend/app/services/` | Shared JSON/CSV analysis orchestration and export serialization |
| `backend/app/domain/` | Calendar, source selection, forecast-only decisions, retrospective pairing, metrics, and coverage |
| `backend/app/persistence/` | Versioned source storage, release publication, and accepted-release analysis adapter |
| `backend/app/ingestion/` | Source client, resumable archives, normalization, coverage validation |
| `backend/migrations/` | Checked-in schema and immutable release-membership migrations |
| `backend/tests/` | Foundation, ingestion, domain arithmetic/temporal integrity, real-source reference, and PostgreSQL checks |
| `data/snapshots/` | Attributed original-response seed and validation manifest |
| `frontend/src/` | React workbench, shared URL state, typed/validated API clients, formatting, and responsive styles |
| `frontend/src/views/` | Decision, retrospective Accuracy, and Data & Methodology views |
| `frontend/src/components/` | Native SVG charts, accessible tables/controls, downloads, loading and error UI |
| `frontend/src/assets/` | Optimized illustrative wind-energy images, generation prompts and provenance |
| `frontend/src/test/` | Attributed frozen API fixtures for offline contract/workflow tests |
| `frontend/scripts/browser-smoke.mjs` | Repeatable real-browser journey and exact-download gate |
| `scripts/` | Running-service, container, wheel and publication checks; prepared local PostgreSQL helper |
| `.github/workflows/ci.yml` | Frozen-data quality and disposable-container CI jobs |
| `Dockerfile`, `compose.yaml` | Combined application image and local PostgreSQL |
| `heroku.yml` | Container deployment manifest for a compatible Heroku app |
| `app.py`, `vercel.json` | Selected Vercel FastAPI entry point and frontend build configuration |
| `docs/PROJECT_PHASES.md` | Phases, dependencies, and completion gates |
| `docs/ARCHITECTURE.md` | System diagram, review boundaries and exact code entry points |
| `docs/decisions/` | Domain and architecture decisions |
| `docs/research/` | Previously completed public-API coverage investigation |
| `docs/PHASE_1_STATUS.md` | Actual implementation checks and external prerequisites |
| `docs/PHASE_2_STATUS.md` | Data-release evidence, database checks, and operational limits |
| `docs/PHASE_3_STATUS.md` | Calculation results, verification, reproduction, and remaining analysis work |
| `docs/METHODOLOGY.md` | Implemented source-time selection, pairing, metrics, and missing-data contract |
| `docs/API.md` | Public filters, response context, CSV interpretation, and error codes |
| `docs/PHASE_4_STATUS.md` | API/export verification, live results, and next-phase boundaries |
| `docs/PHASE_5_STATUS.md` | Frontend tests, real-browser verification, download proof, and remaining release checks |
| `docs/PHASE_6_STATUS.md` | Integrated verification evidence, container checks and remote CI status |
| `docs/PHASE_7_STATUS.md`, `docs/phase-7-evidence.json` | Actual public deployment, logged-out verification, persistence and hosting limits |
| `docs/PHASE_8_STATUS.md`, `docs/phase-8-evidence.json` | Public repository, remote CI evidence, recording and final submission status |
| `docs/VERCEL_SETUP.md` | Deployed architecture, secret configuration, redeployment and recovery procedure |
| `docs/VERIFICATION.md` | Reproduction commands, release gates and security boundaries |
| `docs/LOCAL_READINESS.md` | Verified local handoff, Docker repair, startup and remaining external actions |
| `docs/SECURITY_AND_SCALING.md` | Implemented protections, measured concurrency, reproduction and hosting controls |
| `docs/local-readiness-evidence.json` | Committed-checkout, test, recovery and Desktop-restart evidence |
| `docs/DEMO_SCRIPT.md` | Customer/technical recording script and video checks |
| `docs/RECORDING_CHECKLIST.md` | Nine-minute recording sequence, exact links, figures and unlisted-upload checks |
| `docs/WORKBENCH.md` | Analyst controls, interpretation, sharing, refresh, and downloads |

See the [implementation plan](IMPLEMENTATION_PLAN.md) and [phase breakdown](docs/PROJECT_PHASES.md) for the complete scope. The supplied assignment DOCX, local secrets, environments, caches, generated output, and dependencies are excluded from Git.

## Selected hosting

The public evaluation app runs on Vercel Hobby, with an isolated Neon Free PostgreSQL database in London and the function region configured as `lhr1`. React's compiled assets and the API are served by the same FastAPI application from `app.py`. The canonical URL is public and read-only; existing protection on generated deployment URLs is retained. No paid upgrade was enabled. Free allowances and cold starts apply, and commercial operation requires a separate plan/operational review. See [Vercel setup](docs/VERCEL_SETUP.md) and [the verified release](docs/PHASE_7_STATUS.md). Docker remains the local reproducible runtime.

## AI assistance

OpenAI Codex assisted with requirements analysis, public Elexon API research, implementation planning, scaffolding, code, and verification. The built-in OpenAI image-generation tool produced the two illustrative wind-energy landscapes; [image provenance/prompts](frontend/src/assets/README.md) document their origin. The implementation record states which checks were executed and which remain outstanding. AI assistance does not replace source validation, review, or production acceptance.
