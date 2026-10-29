# Wind Desk

Historical GB wind forecast decision support for January 2026. React and TypeScript frontend, Python FastAPI backend, PostgreSQL, Docker for reproducible local execution, and a prepared Vercel deployment entry point.

**Current implementation: Phase 6 integrated verification.** Decision, Accuracy, and Data & Methodology use the real PostgreSQL release through typed read APIs. Inspect eligible forecasts, publication age, retrospective metrics, coverage, and provenance; share the pinned selection or download matching CSV. The seed contains 19,856 forecast versions and 1,488 WIND actuals. At 09:00, all 744 expected targets pair, with MAE 2,022.47 MW. Repeatable service/browser checks, security backstops, pinned image inputs and CI are now included. See [verification commands](docs/VERIFICATION.md), [Phase 6 evidence](docs/PHASE_6_STATUS.md), and the [workbench guide](docs/WORKBENCH.md).

Public application and demonstration links will be added after deployment and video recording. Neither has been published yet.

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
uv run winddesk seed
uv run winddesk serve --reload
```

In another terminal:

```text
cd frontend
npm ci
npm run dev
```

Open [the local frontend](http://localhost:5173). Vite proxies `/api` and `/health` to the Python service at port 8000. For a single-origin local preview, run `npm run build` in `frontend`, then run the API from the repository root and open [port 8000](http://localhost:8000).

In the prepared Windows workspace, `.tools\uv.exe` is a local portable uv executable; use it in place of `uv` if uv is not on PATH. After dependencies are installed, the backend can also be started with `.\.venv\Scripts\python.exe -m backend.app.cli serve --reload`. A fresh checkout needs its own uv installation. If PowerShell blocks the npm script shim, use `npm.cmd` instead of `npm`.

The complete container entry point is `docker compose up --build`. Compose waits for PostgreSQL, runs a one-off migration/seed service, and then starts the web service. Seeding is idempotent and uses the bundled archive without an external download. Readiness is 200 only when the database and an accepted release are available. Container startup/image execution still requires a working Docker Linux engine; see the status record for checks actually run.

On this prepared Windows workspace, portable PostgreSQL 17.11 provides the local database because Docker Desktop's Linux engine needs repair. Phase 6 verified the image using a separate disposable Ubuntu test engine. The portable database lives under `.tools` and `.cache`, binds only to `127.0.0.1:5432`, and installs no Windows service. Use `scripts/local-postgres.ps1 -Action Status`, `-Action Stop`, or `-Action Start` to control that cluster. Stop it before starting Docker PostgreSQL on the same port, or select alternate Compose ports as in the verification guide. This helper does not install or initialize PostgreSQL for a fresh checkout; use Compose or an explicitly configured PostgreSQL server there.

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
- `GET /api/docs`: generated API documentation.
- `GET /api/openapi.json`: machine-readable API contract.

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

Without this variable, PostgreSQL integration checks are explicitly skipped. Phase 6 passed **90 backend tests with no skips**, including five real PostgreSQL integration tests, and **43 frontend tests**, lint, type checking and the production build. Independent HTTP checks and the real Chrome journey verify cutoff selection, metrics, provenance, guarded downloads and narrow layouts. Frontend tests use attributed frozen fixtures. See [Phase 6 status](docs/PHASE_6_STATUS.md) for actual execution evidence and outstanding remote checks.

The [verification guide](docs/VERIFICATION.md) includes the running-service, browser, packaging, publication-input and isolated-container commands. The [CI workflow](.github/workflows/ci.yml) runs quality checks before image, seed, browser and restart gates, without live Elexon calls. Its remote execution requires the later public repository. The local request quota is a per-process backstop; shared host quotas and trusted proxy identity must be verified during deployment.

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
| `frontend/src/test/` | Attributed frozen API fixtures for offline contract/workflow tests |
| `frontend/scripts/browser-smoke.mjs` | Repeatable real-browser journey and exact-download gate |
| `scripts/` | Running-service, container, wheel and publication checks; prepared local PostgreSQL helper |
| `.github/workflows/ci.yml` | Frozen-data quality and disposable-container CI jobs |
| `Dockerfile`, `compose.yaml` | Combined application image and local PostgreSQL |
| `heroku.yml` | Container deployment manifest for a compatible Heroku app |
| `app.py`, `vercel.json` | Selected Vercel FastAPI entry point and frontend build configuration |
| `docs/PROJECT_PHASES.md` | Phases, dependencies, and completion gates |
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
| `docs/VERIFICATION.md` | Reproduction commands, release gates and security boundaries |
| `docs/WORKBENCH.md` | Analyst controls, interpretation, sharing, refresh, and downloads |

See the [implementation plan](IMPLEMENTATION_PLAN.md) and [phase breakdown](docs/PROJECT_PHASES.md) for the complete scope. The supplied assignment DOCX, local secrets, environments, caches, generated output, and dependencies are excluded from Git.

## Selected hosting

The user has a Vercel account. The prepared route builds React, bundles its compiled files, and serves them through the same FastAPI application from `app.py`. This avoids relying on an unverified multi-service beta. See [Vercel setup](docs/VERCEL_SETUP.md). Authentication, an external PostgreSQL database, budget/plan eligibility, and an actual preview deployment remain to be verified. Docker remains the local reproducible runtime.

## AI assistance

OpenAI Codex assisted with requirements analysis, public Elexon API research, implementation planning, scaffolding, code, and verification. The implementation record states which checks were executed and which remain outstanding. AI assistance does not replace source validation, review, or production acceptance.
