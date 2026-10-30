<div align="center">

# Wind Desk

**Historical wind intelligence for day-ahead electricity decisions.**

Inspect the forecast available at a decision cutoff. Quantify its historical error. Trace every result to its source.

[![Verify Wind Desk](https://github.com/Mayank2142/tme7d41m5t/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Mayank2142/tme7d41m5t/actions/workflows/ci.yml)
![React 19](https://img.shields.io/badge/React-19-264f45?logo=react&logoColor=white)
![Python 3.12](https://img.shields.io/badge/Python-3.12-264f45?logo=python&logoColor=white)
![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17-264f45?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-264f45?logo=docker&logoColor=white)

**[Open live application](https://tme7d41m5t.vercel.app)** · **[Quick start](#quick-start)** · **[Architecture](#architecture)** · **[Verification](#verification)** · **[Demo video](#demo-video)**

</div>

![Wind Desk decision outlook showing the eligible forecast, issue age and hourly wind-generation chart](docs/images/decision-outlook.jpg)

*Actual application capture: 31 January 2026 decision, 09:45 GMT cutoff, delivery on 1 February. The midnight forecast is 10,474 MW and the eligible issue is 15 minutes old.*

## What it solves

A utility buying power a day ahead needs to understand the wind generation expected for delivery and the uncertainty around that forecast. Wind Desk answers two specific questions using public Elexon data:

1. **What wind forecast was available before this purchase decision?**
2. **How accurately did forecasts selected by the same rule perform historically?**

The public, read-only pilot covers **January 2026 purchase decisions** for national Great Britain wind generation. It combines a forecast-only decision replay, retrospective accuracy analysis and inspectable source provenance. Demand, prices, existing positions and portfolio entitlement are outside the supplied dataset, so the product supports analysis rather than calculating a utility-specific purchase quantity.

| Accepted source snapshot | January comparison | Reproducible delivery |
| --- | --- | --- |
| **19,856** forecast versions | **744 / 744** valid native target pairs | **107** backend + **47** frontend tests |
| **1,488** reported WIND actuals | **31** purchase-decision dates | Docker, real-browser checks and public Linux CI |

## Explore the workspace

| View | Analyst workflow |
| --- | --- |
| **[Decision outlook](https://tme7d41m5t.vercel.app/decision)** | Select a January decision and cutoff; inspect next-day forecasts, publication time, age and coverage; navigate exact chart values with the keyboard; export eligible forecasts. |
| **[Forecast accuracy](https://tme7d41m5t.vercel.app/accuracy)** | Compare selected forecasts with reported actuals; inspect MAE, RMSE, signed bias and P90 absolute error; drill into a day or large miss; reconcile coverage and export the comparison. |
| **[Data & methodology](https://tme7d41m5t.vercel.app/methodology)** | Review the source snapshot, date/comparison rules, validation ledger, original request links, response checksums and full analysis references. |

Applied filters and the dataset release remain in shareable URLs. Draft edits are clearly marked; downloads stay tied to the applied analysis. Failed refreshes preserve the last successful view with an explicit message. The responsive interface includes native SVG charts, accessible data tables, keyboard controls, reference dialogs and reduced-motion support.

<details>
<summary><strong>See the Forecast accuracy screen</strong></summary>

![Full January forecast accuracy view with error metrics, forecast-versus-actual chart, daily drill-down and coverage](docs/images/forecast-accuracy.jpg)

*Full January at 09:45 GMT: 744 pairs, MAE 1,995.6 MW and signed bias +1,728.0 MW.*

</details>

<details>
<summary><strong>See the Data & methodology screen</strong></summary>

![Data and methodology view with accepted source counts, comparison rules and provenance table](docs/images/data-methodology.jpg)

*Source and calculation rules are inspectable alongside the original Elexon request references.*

</details>

Screenshots show the running product. [Capture details](docs/images/README.md) record their source and selection.

## Technology stack

| Layer | Technologies | Role in this project |
| --- | --- | --- |
| Frontend | **React 19, TypeScript 7, Vite 8** | Component-based analyst workspace, typed contracts and compiled static assets. |
| Client data/state | **TanStack Query 5, Fetch API, URL state** | Filter-aware requests, cancellation, loading/error handling, refresh and shareable selections. |
| Visualization/UI | **Native SVG, CSS, native HTML dialogs** | Inspectable charts, responsive layouts, subtle motion, keyboard interaction and reduced-motion support. |
| Backend | **Python 3.12, FastAPI, Pydantic, Uvicorn** | Typed read APIs, configuration validation, safe errors and local/container serving. |
| Persistence | **PostgreSQL 17, SQLAlchemy 2, Psycopg 3, Alembic** | Versioned source facts, immutable release membership, bound queries and checked-in migrations. |
| External data | **Elexon Insights: WINDFOR and FUELHH WIND** | The only analytical data sources; original responses and checksums are preserved. |
| Testing/quality | **pytest, Vitest, Testing Library, Playwright, Ruff, Biome** | Domain/integration tests, frontend workflows, real-browser/export checks and lint/format validation. |
| Delivery | **Docker/Compose, GitHub Actions, Vercel, Neon PostgreSQL** | Reproducible local runtime, automated verification and the public evaluation deployment. |
| Dependency management | **uv, npm; committed lockfiles** | Reproducible Python/frontend installations and dependency audits. |

Exact dependency versions are recorded in [uv.lock](uv.lock) and [package-lock.json](frontend/package-lock.json). Native development and CI use **Node 24**. There is **no predictive ML model or AI service in the analytical request path**: this application evaluates Elexon's published forecasts.

## Quick start

### Docker — complete application

Install Git and Docker with a working Linux-container engine. This route builds the frontend/backend, starts PostgreSQL, runs migrations and imports the bundled real-data seed; host Python and Node installations are unnecessary.

```sh
git clone https://github.com/Mayank2142/tme7d41m5t.git
cd tme7d41m5t
```

Copy the local environment template:

| Shell | Command |
| --- | --- |
| macOS / Linux | `cp .env.example .env` |
| Windows PowerShell | `Copy-Item .env.example .env` |

```sh
docker compose up --build --detach --wait web
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)**. Local [API documentation](http://127.0.0.1:8000/api/docs) and [readiness](http://127.0.0.1:8000/health/ready) are available on the same origin. Readiness requires both the database and an accepted release. Startup uses the bundled archive, without downloading new Elexon data.

```sh
docker compose logs --tail=80 web initialize
docker compose stop
```

Stopping retains the database volume. The template passwords are **development values**; hosted credentials are configured separately.

<details>
<summary><strong>Windows startup helper and alternate ports</strong></summary>

From a checkout with Docker Desktop running:

```powershell
.\scripts\local.ps1 -Action Start
.\scripts\local.ps1 -Action Status
.\scripts\local.ps1 -Action Stop
```

The helper owns a scoped Compose project, checks readiness and preserves its volume. For occupied ports, supply `-HttpPort 18000 -DatabasePort 15432`. Use one startup route at a time. See [local handoff](docs/LOCAL_READINESS.md) for ownership guards and troubleshooting.

</details>

<details>
<summary><strong>Native development with frontend hot reload</strong></summary>

Prerequisites: Python 3.12, Node 24, npm, uv and PostgreSQL (the database can run in Docker). Copy `.env.example` as above, then:

```sh
docker compose up -d postgres
uv sync --frozen
uv run winddesk check-db
uv run winddesk seed --configure-reader
```

Run the web process using the restricted reader. PowerShell:

```powershell
$env:GRID_DATABASE_URL = 'postgresql+psycopg://winddesk_reader:winddesk_local@127.0.0.1:5432/winddesk'
uv run winddesk serve --reload
```

Bash:

```sh
export GRID_DATABASE_URL='postgresql+psycopg://winddesk_reader:winddesk_local@127.0.0.1:5432/winddesk'
uv run winddesk serve --reload
```

In another terminal:

```sh
npm ci --prefix frontend
npm run dev --prefix frontend
```

Open [localhost:5173](http://localhost:5173). Vite proxies `/api` and `/health` to Python on port 8000. `npm run build --prefix frontend` produces the static frontend for single-origin Python serving. Keep operator credentials in a separate session for migrations/imports.

</details>

## Architecture

```mermaid
flowchart LR
    User["Analyst browser<br/>React + TypeScript"] --> Edge["Vercel HTTPS<br/>Project firewall"]
    Edge --> API["FastAPI<br/>Read APIs + built frontend"]
    API --> Service["Bounded caches<br/>Analysis + CSV services"]
    Service --> Domain["Pure domain logic<br/>Cutoff, pairing, metrics"]
    Service --> Reader["Restricted database reader"]
    Reader --> DB[("PostgreSQL<br/>Immutable accepted releases")]
    Elexon["Elexon<br/>WINDFOR + FUELHH WIND"] --> CLI["Operator CLI<br/>Fetch, validate, migrate, seed"]
    Archive["Bundled source archive"] --> CLI
    CLI --> DB
```

**One analyst request:** React validates the applied filters → Fetch requests a typed API route → FastAPI resolves an accepted release → the reader loads its source versions → pure domain functions select and compare records → the service returns results and a guarded export URL → React displays the same release and context.

**Separate write path:** migrations and ingestion run through the operator CLI. Web requests read the accepted dataset and do not trigger live Elexon downloads. An invalid candidate import cannot replace the active accepted release.

The [architecture/code map](docs/ARCHITECTURE.md) links each design concern to its implementation. [API contracts](docs/API.md) document filters, context hashing, error reasons and CSV columns.

## Data and calculation rules

| Rule | Implemented behavior |
| --- | --- |
| Decision window | 1–31 January 2026, in `Europe/London`; next-day delivery spans 2 January–1 February. |
| Cutoff | Configurable local `HH:MM`; 09:00 is an illustrative desk assumption, not a verified auction gate closure. |
| Forecast selection | For each target, choose the latest publication **at or before** the cutoff, then validate that key. A null/conflicting latest issue stays invalid; it does not silently fall back. |
| Decision isolation | Decision JSON/CSV load forecasts only and exclude future actuals and retrospective errors. |
| Comparison | `source_timestamp_v1`: compare equal source `startTime` values. Native forecasts are hourly; actuals are half-hourly. Forecasts are not interpolated between targets. |
| Actual vintage | Latest actual publication within the frozen accepted release; reported outturn can include estimates. |
| Missing data | Explicit missing/invalid reasons and coverage. Missing generation is not zero; no-pair metrics are null. |
| Error direction | **Forecast − actual**. Positive bias means wind was overforecast on average. |
| Reproducibility | Context SHA-256 includes release, parser, policies, applied dates/cutoff and build. CSV is pinned to that context; stale downloads are rejected. |

The Accuracy export retains all **1,488 actual half-hours**, marking the **744 native comparison targets** and valid metric contributions explicitly. Matching timestamps does not establish identical averaging semantics or a full-hour energy profile. [Read the complete methodology](docs/METHODOLOGY.md).

### Verified January results

Full January decisions, the accepted bundled release and `source_timestamp_v1`; units are MW.

| Local cutoff | Valid pairs | MAE | RMSE | Signed bias | P90 absolute error |
| --- | ---: | ---: | ---: | ---: | ---: |
| 09:00 GMT | 744 | 2,022.47 | 2,497.41 | +1,745.94 | 4,154.40 |
| 09:45 GMT | 744 | 1,995.57 | 2,498.82 | +1,727.98 | 4,183.90 |

These are descriptive historical results. P90 is not a calibrated future confidence interval or procurement buffer. Source publication time models historical eligibility; later retrieval does not prove receipt by a trading desk in January.

## API and operator commands

| Read endpoint | Purpose |
| --- | --- |
| `GET /api/v1/config` | Non-secret scope, policies, defaults and accepted dataset status |
| `GET /api/v1/decision-view` | Forecast-only replay for `decision_date`, `cutoff_local` and optional pinned `release_id` |
| `GET /api/v1/accuracy` | Retrospective pairs, metrics, daily results and coverage for a decision-date range |
| `GET /api/v1/data-quality` | Validation, raw-response provenance and original source references |
| `GET /api/v1/export.csv` | Context-guarded Decision/Accuracy CSV; follow the response's `export_url` |
| `GET /health/live`, `GET /health/ready` | Process liveness and accepted-data/database readiness |

`/api/docs` and `/api/openapi.json` are available in local development and disabled by default in production.

<details>
<summary><strong>Ingestion, validation and analysis CLI</strong></summary>

| Command | Purpose |
| --- | --- |
| `uv run winddesk migrate` | Apply checked-in Alembic migrations |
| `uv run winddesk seed` | Import the bundled archive idempotently, validating before acceptance |
| `uv run winddesk fetch` | Fetch missing January request windows into a resumable archive |
| `uv run winddesk backfill --refresh` | Explicitly fetch, validate and import a new source vintage |
| `uv run winddesk validate --report output/validation.json` | Check raw checksums, normalized coverage and validation results |
| `uv run winddesk export-release --output output/recovered.json.gz` | Recover original accepted-release response payloads from PostgreSQL |
| `uv run winddesk analyze --cutoff 09:00 --output output/analysis.json` | Reproduce January accuracy and selected points from stored data |

The default seed is `data/snapshots/january_2026.json.gz`. Complete archives are reused unless explicitly refreshed; failed downloads retain resumable checkpoints. Old release membership stays fixed across parser revisions. `seed --allow-partial` is an explicit operator override, remains labeled partial and should not conceal gaps. See [data pipeline evidence](docs/PHASE_2_STATUS.md).

</details>

## Verification

The [verified public Linux run](https://github.com/Mayank2142/tme7d41m5t/actions/runs/41097891003) passed **107 backend tests with no skips**, **47 frontend tests**, lint/type/build checks, wheel-resource verification, dependency audits and both CI jobs. The CI badge reports the latest `main` run independently.

The container gate builds from the public commit, initializes a fresh PostgreSQL volume, checks runtime restrictions, exercises real API/CSV/browser flows, replays the seed, restarts database/web and compares unchanged result fingerprints. Browser checks cover cutoff changes, exact downloads, keyboard/reference dialogs, reduced motion and 1440/390/320-pixel layouts. Ordinary tests/CI use the frozen Elexon archive rather than live data calls.

```sh
uv sync --frozen
npm ci --prefix frontend
uv run ruff check backend scripts
uv run ruff format --check backend scripts
uv run pytest
npm run lint --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend
```

Set `GRID_TEST_DATABASE_URL` to a **dedicated local/test PostgreSQL database** to include integration tests. The test operator needs schema/role-management permissions; never point it at production. Without that variable, PostgreSQL tests are explicitly skipped. [Verification commands](docs/VERIFICATION.md) cover real-browser, service, packaging and disposable-container gates.

The dated dependency checks reported zero known advisories (41 Python production packages and the frontend lockfile). This records advisory status at the check time. [Public CI evidence](docs/PHASE_8_STATUS.md) preserves test counts, source/image identities and restart fingerprints.

## Security, scalability and deployment

The dashboard is intentionally **public and read-only**, using public national wind data. There is no user sign-in or purchase-execution API.

- **Least privilege:** a separate web database login with restricted SELECT grants; no writes, schema changes, raw-payload or ingestion-record access. Operator credentials are kept outside the web runtime.
- **Request protection:** typed/bounded filters, duplicate-query rejection, bound SQL values, safe error responses, CSV formula neutralization, exact host allowlisting, request-size limits, cross-site API rejection and restrictive browser headers.
- **Resource bounds:** per-process caches with bounded size/lifetime and shared same-key work; request/admission limits, database timeouts and a controlled connection budget. These are not a global distributed quota.
- **Delivery controls:** verified PostgreSQL TLS, secrets outside source/frontend bundles, production API docs off, non-root/read-only local containers, locked dependencies and pinned CI/image inputs.
- **Hosted setup:** Vercel serves built React and FastAPI from one origin, with the function region configured as London `lhr1`. Neon Free hosts the separate London PostgreSQL database. HTTPS, automatic platform DDoS mitigation and two free edge deny rules were verified. No paid upgrade was enabled.

Vercel builds this application **from source**; Docker provides the local reproducible runtime. Deployment is currently through the authorized CLI; the GitHub workflow verifies code and does not deploy it automatically. See [Vercel/operator guide](docs/VERCEL_SETUP.md) and [deployed-source evidence](docs/PHASE_7_STATUS.md).

This is a tested historical evaluation pilot. Free quotas/cold starts apply. Sustained cloud capacity, distributed limits, trusted end-user proxy identity, owned alerts, measured hosted recovery, commercial hosting eligibility and client acceptance remain operational work. The local 50-client/200-request burst was a local API measurement, not an internet user-capacity guarantee. [Security and scaling](docs/SECURITY_AND_SCALING.md) explains the measured workload and practical limits.

## Repository guide

```text
.
├── backend/
│   ├── app/
│   │   ├── api/           # Validated read routes and safe errors
│   │   ├── domain/        # Calendar, source selection, pairing and metrics
│   │   ├── ingestion/     # Elexon requests, archives and validation
│   │   ├── persistence/   # Models, releases, reader and permissions
│   │   └── services/      # Shared analysis, bounded caching and CSV
│   ├── migrations/        # Alembic schema/release migrations
│   └── tests/             # Domain, API, security and PostgreSQL checks
├── frontend/
│   ├── src/
│   │   ├── api/           # Typed and runtime-validated HTTP contracts
│   │   ├── components/    # Charts, references, controls and visual scene
│   │   ├── views/         # Decision, Accuracy and Methodology
│   │   ├── assets/        # Self-hosted imagery and provenance
│   │   └── test/          # Attributed frozen source fixtures
│   └── scripts/           # Real-browser workflow/download verification
├── data/                  # Original-response seed, manifest and attribution
├── docs/                  # Architecture, methods, evidence and handoff
│   └── images/            # Committed real-product screenshots
├── scripts/               # Local startup, service/container/package checks
├── .github/workflows/     # Public Linux quality/container CI
├── app.py                 # Vercel FastAPI entry point
├── Dockerfile             # Multi-stage combined application image
├── compose.yaml           # Local database, initializer and web service
├── vercel.json            # Vercel build/bundle/runtime configuration
├── pyproject.toml / uv.lock
└── frontend/package.json / package-lock.json
```

| Read next | Purpose |
| --- | --- |
| [Workbench guide](docs/WORKBENCH.md) | Controls, interpretation, sharing and downloads |
| [Architecture](docs/ARCHITECTURE.md) · [Methodology](docs/METHODOLOGY.md) · [API](docs/API.md) | Technical review and calculation contracts |
| [Verification](docs/VERIFICATION.md) · [Security](docs/SECURITY_AND_SCALING.md) | Reproduce checks and understand protection/capacity limits |
| [Deployment](docs/PHASE_7_STATUS.md) · [Publication/CI](docs/PHASE_8_STATUS.md) | Actual executed evidence and outstanding submission work |
| [Implementation plan](IMPLEMENTATION_PLAN.md) · [Phases](docs/PROJECT_PHASES.md) | Scope, sequencing and operational acceptance gates |
| [Local handoff](docs/LOCAL_READINESS.md) · [Vercel guide](docs/VERCEL_SETUP.md) | Startup, recovery and environment ownership |

Secrets, assignment DOCX files, local environments, generated media/output, caches and dependencies are excluded from Git. Historical phase records retain their original results; current evidence links distinguish later improvements.

## Demo video

![Wind Desk product demo and technical review](docs/images/video-thumbnail.jpg)

The complete **9:40 Full HD video** has been rendered locally with AI-generated Indian English narration, real application demonstrations, architecture/code explanations, synchronized subtitles, quiet music and chapter markers. [Production record, storyboard and verification](docs/VIDEO_PRODUCTION.md) document the result.

**Unlisted YouTube watch link: pending upload and playback verification.** The rendered MP4 is retained in the producing workspace under `output/video/wind-desk-demo.mp4`; large generated media is excluded from Git. The assignment has not been submitted. Cumulative actual effort against the original sixteen-hour limit has not been fully reconciled.

## Data attribution and AI assistance

**Contains BMRS data © Elexon Limited copyright and database right 2026.** The application and bundled archive preserve the applicable attribution. See [source-data attribution and licence](data/ATTRIBUTION.md); data rights are separate from application-code licensing.

OpenAI Codex assisted with requirements analysis, Elexon research, planning, implementation, documentation and verification. The built-in OpenAI image-generation tool created the two illustrative wind-energy landscapes used by the interface; [asset provenance and prompts](frontend/src/assets/README.md) record their origin. Those landscapes do not represent measured January weather or identified generating sites. Video narration/production assistance is disclosed with the resulting media. All generation values and quantitative results come from the allowed Elexon data, under the documented policies.
