# Rendered video voiceover and storyboard

Generated on 31 October 2026 from the inspected application and repository. The sequence is the actual final edit; chapter times use the rendered timeline. [Production and verification record](../VIDEO_PRODUCTION.md).

## 00:00 · WIND DESK

Requested topic: 1. Visual: intro. Duration: 19.43 seconds.

Welcome to Wind Desk, a historical wind intelligence workbench for electricity procurement teams. This is a walkthrough of the real application and its implementation. We will replay a January purchase decision, quantify forecast error, and follow the data from Elexon through Python and Postgres to the React dashboard.

## 00:19 · A decision before delivery

Requested topic: 2. Visual: problem. Duration: 19.23 seconds.

A utility needs to buy electricity before the delivery day, while wind generation depends on weather. The analyst needs the forecast available at the decision deadline, together with a defensible view of its uncertainty. Looking only at the latest number today cannot reconstruct what was known at an earlier cutoff.

## 00:38 · Two questions. One reproducible record.

Requested topic: 2. Visual: solution. Duration: 23.77 seconds.

Wind Desk separates those two questions. Decision outlook contains eligible forecasts only. Accuracy compares them with later reported generation. Both retain the selected release, cutoff and source references. This pilot uses only Elexon national wind data. It does not infer the amount a particular utility should buy without demand and existing positions.

## 01:02 · Live: January 31 at 09:00

Requested topic: 6. Visual: live. Duration: 21.47 seconds.

Here is the actual deployed Decision view. January thirty-first at nine a.m. concerns delivery on February first. All twenty-four native forecast targets are available. The midnight forecast is ten thousand and ninety-nine megawatts. Its selected issue is seven thirty a.m., so the age at the cutoff is one hour and thirty minutes.

## 01:23 · Live: move the cutoff to 09:45

Requested topic: 6. Visual: live. Duration: 22.87 seconds.

Now the cutoff changes to nine forty-five. The unapplied warning keeps the current analysis and download from being confused with an edit. After Apply, the nine thirty issue becomes eligible. The midnight forecast becomes ten thousand four hundred and seventy-four megawatts, and its age becomes fifteen minutes. The chart and publication ledger expose exact target values.

## 01:46 · Live: quantify the miss

Requested topic: 6. Visual: live. Duration: 25.10 seconds.

Accuracy evaluates the full January range at this cutoff. All seven hundred and forty-four native targets pair. Mean absolute error is about one thousand nine hundred and ninety-six megawatts. Root mean square error is about two thousand four hundred and ninety-nine. Positive bias shows average overforecasting. P ninety absolute error is a historical statistic, not a guaranteed future buffer.

## 02:11 · Live: drill down and export

Requested topic: 6. Visual: live. Duration: 21.80 seconds.

Selecting a decision day narrows the historical review. The chart, coverage, error summary and C S V follow that selection. The export retains all actual half-hours and explicitly marks native comparison targets. A saved view keeps its release when reopened. Missing values remain gaps with reasons, rather than becoming zero generation.

## 02:33 · Live: inspect the source

Requested topic: 6. Visual: live. Duration: 22.53 seconds.

Data and methodology shows nineteen thousand eight hundred and fifty-six forecast versions and one thousand four hundred and eighty-eight actual observations. Source rows open response references and checksums. The analysis dialog exposes the full context and release identities. These references let a reviewer trace a visible figure back to the accepted source evidence.

## 02:56 · Select the latest eligible key first

Requested topic: 5. Visual: selection. Duration: 20.30 seconds.

For every delivery target, the selector first restricts publications to those at or before the cutoff. It chooses the latest eligible key, and only then checks quality. A null or conflicting latest issue stays invalid; it does not silently fall back to an older valid forecast. Decision analysis does not load actuals.

## 03:16 · Metrics follow the documented comparison

Requested topic: 7. Visual: metrics. Duration: 24.80 seconds.

Errors are forecast minus actual. The metrics module calculates mean absolute error, root mean square error, signed bias and an interpolated ninetieth percentile. With no valid pairs, metrics are null. Hourly forecast targets match actuals at equal source timestamps. The intervening actual half-hours remain in exports; forecasts are not invented between hourly targets.

## 03:41 · One origin for the analyst

Requested topic: 4. Visual: architecture. Duration: 23.13 seconds.

The browser reaches the Vercel HTTPS endpoint and project firewall. FastAPI serves both the compiled React assets and read APIs from that origin. Analysis services use bounded caches and a restricted database reader. Pure domain functions calculate the result. The response includes an analysis identity and a matching guarded C S V download.

## 04:04 · A separate operator write path

Requested topic: 4. Visual: database. Duration: 24.43 seconds.

Ingestion is separate from browsing. The operator command fetches or replays original Elexon responses, validates them, and publishes an accepted release. Database tables retain raw batches, forecast and actual versions, immutable membership, and an active-release pointer. A failed candidate does not replace accepted data. The web function receives only the restricted reader credential.

## 04:28 · From an edit to an API request

Requested topic: 5. Visual: flow. Duration: 20.37 seconds.

When the analyst edits a date or cutoff, React keeps the draft distinct from the applied result. Applying a valid selection updates the U R L and query key. Fetch sends the selected date, local cutoff and release to the decision-view endpoint. FastAPI rejects invalid or duplicate filters before analysis begins.

## 04:49 · Frontend: a consistent analyst workspace

Requested topic: 3. Visual: stack. Duration: 24.60 seconds.

React builds the three analyst views. TypeScript and runtime response validation help catch contract mismatches. Vite provides development and production builds. TanStack Query manages filter-specific requests, cancellation and refresh. Native S V G charts and HTML dialogs keep exact values and references keyboard-accessible, with responsive layouts and reduced-motion support.

## 05:13 · Backend and durable data

Requested topic: 3. Visual: stack. Duration: 22.77 seconds.

FastAPI exposes typed read routes, while Pydantic validates filters and response contracts. Python domain functions contain selection and metric rules independently of H T T P. SQLAlchemy and Psycopg connect to Postgres using bound parameters and a small pool. Alembic versions the schema. This separation makes the business rules independently testable.

## 05:36 · Tools and integrations

Requested topic: 3. Visual: stack. Duration: 27.37 seconds.

Elexon is the only analytical data integration. Docker Compose reproduces the application locally. GitHub Actions runs quality and container checks. Vercel hosts the web application, and Neon hosts Postgres. Pytest, Vitest, Testing Library, Playwright, Ruff and Biome verify the implementation. Locked dependencies make those environments reproducible. There is no predictive A I model in the application.

## 06:03 · Return a result with its evidence

Requested topic: 5. Visual: flow. Duration: 23.20 seconds.

The service resolves the accepted release before using its cache. Its context includes the release, parser, policies, applied filters and build identifier. A canonical hash pins the analysis and export. React checks the returned contract and displays values, coverage and issue age. A stale export context is rejected instead of returning a different analysis.

## 06:27 · A codebase organized around integrity

Requested topic: 7. Visual: repository. Duration: 26.33 seconds.

The repository separates frontend views and typed clients from Python A P I routes, services, domain logic and persistence. Migrations and operator ingestion have their own modules. Source fixtures, tests and verification scripts are explicit. The root README explains startup, the technology stack, methodology, deployment evidence and A I assistance. Local secrets and generated output stay outside Git.

## 06:53 · The forecast-only boundary is explicit

Requested topic: 7. Visual: code. Duration: 20.37 seconds.

In the decision service, the reader loads forecasts for the pinned release and passes them to decision analysis. It never loads actuals here. The source selector and metric functions are separate modules. Tests cover cutoff equality, invalid latest keys, revised actuals, missing data and the January to February boundary.

## 07:13 · Public access. Restricted privileges.

Requested topic: 8. Visual: security. Duration: 23.73 seconds.

This is deliberately a public, read-only dashboard, with no user authentication flow. Protection relies on request validation, restrictive browser headers, safe errors and a separate database reader. The reader cannot write, change schema, or access raw payload bytes. Verified T L S protects the database connection. Operator credentials are absent from the web runtime.

## 07:37 · Bounded work instead of unbounded promises

Requested topic: 8. Visual: performance. Duration: 24.30 seconds.

Caches have bounded size and lifetime, and concurrent requests for one key share a calculation. Database pools and timeouts constrain resource use. A local fifty-client test completed two hundred requests at roughly four hundred and ninety-three milliseconds at the ninety-fifth percentile, using a test-only quota. This is local API evidence, not a hosted capacity or availability guarantee.

## 08:01 · Proof from a clean Linux runner

Requested topic: 8. Visual: verification. Duration: 25.90 seconds.

The published continuous-integration run passed one hundred and seven backend tests with no skips and forty-seven frontend tests. It also built Docker, replayed the real seed, exercised the browser and exact downloads, restarted Postgres and web, and compared unchanged fingerprints. The clean runner exposed database-reader isolation and clipboard-permission test assumptions; both were corrected without changing the production analysis.

## 08:27 · What is actually deployed

Requested topic: 9. Visual: deployment. Duration: 24.20 seconds.

Vercel imports the root FastAPI application, builds React, and bundles its compiled assets. The function region is configured as London, with external Neon Postgres in London. The selected plans are free tiers. The function uses verified T L S, one pooled connection per instance and a reader-role connection cap. Database initialization is a separate operator step.

## 08:52 · How updates reach reviewers

Requested topic: 9. Visual: deployment. Duration: 25.53 seconds.

GitHub Actions verifies changes; it does not automatically deploy this project. An authorized Vercel C L I deployment publishes a reviewed revision. The deployment record identifies the source and dataset. Later documentation and test commits differ from the hosted build, while a comparison verified eighty-nine identical runtime inputs. Replacing the hosted application preserved its accepted data and results.

## 09:17 · WIND DESK

Requested topic: 10. Visual: outro. Duration: 22.97 seconds.

Wind Desk connects a practical analyst workflow with explicit temporal rules, durable source evidence and repeatable verification. Its next operational steps are agreed trading cutoffs, scheduled receipt-aware data, distributed capacity controls, monitored recovery and client acceptance. Explore the public application and repository shown here. Thank you for reviewing the project.

