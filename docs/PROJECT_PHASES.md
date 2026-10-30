# Project Phases and Completion Gates

This is the execution sequence for the [implementation plan](../IMPLEMENTATION_PLAN.md). Phases 1–8 were planned against a sixteen-hour total-effort budget, including contingency. Actual cumulative effort has not been fully reconciled; the estimates below do not establish compliance with that limit. Phases 9–11 describe subsequent work before a utility uses the application operationally; estimate and authorize that work separately.

Phases 1–7 are implemented and verified for the evaluation pilot, including later frontend and security enhancements. The [public app](https://tme7d41m5t.vercel.app) passed logged-out analyst, CSV, security and replacement-deployment persistence checks. [Phase 7 status](PHASE_7_STATUS.md), [local readiness](LOCAL_READINESS.md) and [security/scaling](SECURITY_AND_SCALING.md) record the executed evidence. Phase 8 has published the anonymous-name [public repository](https://github.com/Mayank2142/tme7d41m5t) and passed full Linux quality/container CI; [Phase 8 evidence](PHASE_8_STATUS.md) records the result. The own-voice video and submission remain outstanding. The sixteen-hour limit is not a fresh budget starting after planning.

## Phase overview

| Phase | Focus | Planned effort | Required outcome |
| --- | --- | ---: | --- |
| 1 | Requirements, architecture, and project foundation | 1.25 hours | Agreed pilot policies and a working application skeleton |
| 2 | Data ingestion and persistence | 2.00 hours | A reproducible, validated January dataset release |
| 3 | Forecast selection and accuracy engine | 1.75 hours | Correct cutoff selection, comparison, metrics, and coverage |
| 4 | Backend APIs and exports | 1.25 hours | Typed, consistent read endpoints and CSV |
| 5 | Frontend dashboard | 2.50 hours | Complete analyst journey across the three views |
| 6 | Integrated verification, Docker, and CI | 2.25 hours | A tested application that starts from a fresh checkout |
| 7 | Public deployment and verification | 1.00 hour | A durable public HTTPS application |
| 8 | Documentation, demonstration, and submission | 2.75 hours | Complete repository, video, checked links, and form submission |
| Reserve | Contingency across phases | 1.25 hours | Time protected for failures and corrections |
| | **Assignment total** | **16.00 hours** | |
| 9 | Operational data reliability | Separately estimated | Scheduled, monitored ingestion and frozen operational decisions |
| 10 | Security, access, and recovery | Separately estimated | Controlled access and proven recovery procedures |
| 11 | Client acceptance and production launch | Separately estimated | Domain approval, measured service performance, and operational ownership |

Move forward when the current phase's completion gate is satisfied. Develop unit tests with the domain logic; Phase 6 consolidates integrated verification rather than postponing all testing. Confirm hosting feasibility in Phase 1 and perform an early deployment smoke test as soon as the skeleton can run. Phase 7 releases and checks the completed pilot.

## Phase 1 Requirements architecture and project foundation

**Objective:** establish an unambiguous scope and a working technical starting point.

Tasks:

- Reuse the completed source-document review and Elexon coverage investigation.
- Record the January decision-date interpretation, next-day delivery window, illustrative 09:00 Europe/London cutoff, and default `source_timestamp_v1` comparison.
- Confirm the allowed hosting route, account access, database availability, and cost ownership.
- Set up React with TypeScript, FastAPI, PostgreSQL configuration, dependency locks, and the initial repository structure.
- Add health routes, a basic frontend-to-backend request, and an environment-variable example. Prepare an early deployment smoke test.

**Deliverables:** recorded assumptions, architecture outline, application skeleton, and confirmed hosting path.

**Completion gate:** the frontend can call the Python service, configuration is validated, and a compatible deployment route has been established.

**Backlog mapping:** P0-01 and P0-02. **Current status:** application foundation implemented; the user selected Vercel. Verification and unresolved external prerequisites are recorded in [Phase 1 status](PHASE_1_STATUS.md).

## Phase 2 Data ingestion and persistence

**Objective:** convert the allowed Elexon data into a durable, traceable dataset.

Tasks:

- Implement migrations, ingestion-run records, immutable raw-response storage, and versioned forecast/actual rows.
- Backfill WINDFOR publication windows and FUELHH WIND settlement dates.
- Cover January decisions and delivery dates from 2 January through 1 February, including the relevant December publication lookback.
- Validate timestamps, fuel, resolution, nulls, duplicate versions, conflicting source keys, and expected coverage.
- Publish an immutable accepted dataset release and create the real-data seed and manifest.

**Deliverables:** ingestion CLI, PostgreSQL schema, raw archive, quality report, accepted release, and seed artifact.

**Completion gate:** re-ingestion is idempotent; the January coverage ledger reconciles; every retained record has source provenance; invalid candidate releases cannot replace an accepted release.

**Dependency:** Phase 1. **Backlog mapping:** P0-03 and P0-04. **Current status:** implemented and verified against local PostgreSQL, including real backfill, idempotency, candidate rejection, parser isolation, archive replay, and restart persistence; see [Phase 2 status](PHASE_2_STATUS.md).

## Phase 3 Forecast selection and accuracy engine

**Objective:** implement the business rules that make the analysis defensible.

Tasks:

- Construct UK calendar boundaries correctly and select the latest source key at or before each decision cutoff, independently per target.
- Validate the selected latest key before returning its value; do not hide a null or conflict by silently choosing an older valid record.
- Match forecast and actual values at equal source timestamps under the default policy.
- Calculate MAE, RMSE, signed bias, P90 absolute error, and a reconciled coverage ledger.
- Test cutoff equality, post-cutoff exclusion, January/February boundaries, missing values, actual vintages, zero pairs, and independently calculated examples.

**Deliverables:** pure domain modules, versioned calculation policies, and domain tests.

**Completion gate:** hand-calculated fixtures pass; all expected targets have an explicit state; neither future forecasts nor future actuals enter decision replay. Optional hourly-average analysis remains a distinct policy.

**Dependency:** Phase 2 for real-data validation; synthetic domain fixtures can be developed earlier. **Backlog mapping:** P0-05 and P0-06. **Current status:** implemented and verified with hand-calculated examples, all target states, source-time pairing, revised actuals, cutoff and calendar boundaries, independent raw-source calculations, and the pinned PostgreSQL adapter. See [Phase 3 status](PHASE_3_STATUS.md). The optional hourly-average policy remains deferred.

## Phase 4 Backend APIs and exports

**Objective:** expose the same analysis consistently to the interface and downloads.

Tasks:

- Implement configuration, Decision, Accuracy, data-quality, and CSV endpoints.
- Validate dates, ranges, cutoff values, release identifiers, and comparison policies.
- Return release identity, analysis context, source provenance, coverage, and stable error reasons.
- Keep Decision response types free of future actuals and retrospective summaries.
- Pin a single dataset release for each analysis and its export.

**Deliverables:** typed API contracts, read endpoints, CSV export, and contract tests.

**Completion gate:** identical filters and release produce matching API and export results; invalid input is explained; valid missing-data cases return coverage and nulls rather than invented zeros.

**Dependencies:** Phases 2 and 3. **Backlog mapping:** P0-07. **Current status:** implemented with distinct Decision/Accuracy schemas, bounded filters, immutable-release reads, deterministic contexts, pinned quality/download URLs, coverage-preserving CSV, and safe error responses. See [Phase 4 verification](PHASE_4_STATUS.md) and the [API contract](API.md).

## Phase 5 Frontend dashboard

**Objective:** provide a clear, usable procurement-analysis workflow.

Tasks:

- Build the Decision view with date/cutoff controls, delivery bounds, forecast points, publication times, age, and coverage.
- Build the Accuracy view with forecast/actual charts, error metrics, daily analysis, large misses, and export.
- Build the Data and Methodology view with source scope, policies, release provenance, and quality information.
- Preserve filters in shareable URLs and keep labels, data, and downloads synchronized during changes.
- Implement loading, empty, partial, unavailable, and failed-refresh states, with keyboard-accessible controls and readable tables.

**Deliverables:** three connected views and the complete required analyst journey.

**Completion gate:** a user can inspect a January decision, change its cutoff, understand historical error, identify missing data, and download the exact selected records.

**Dependency:** Phase 4. **Backlog mapping:** P0-08 and P0-09. **Current status:** implemented and verified with three connected real-data views, shared URL filters and release, explicit loading/empty/partial/error/failed-refresh states, native charts and source tables, keyboard inspection, actual guarded downloads, and desktop/narrow layouts. See [Phase 5 status](PHASE_5_STATUS.md).

## Phase 6 Integrated verification Docker and CI

**Objective:** prove the application works as a reproducible whole.

Tasks:

- Run PostgreSQL integration tests and the critical browser journey.
- Verify comparison examples, latest-key integrity, historical isolation, release consistency, and CSV agreement.
- Check keyboard navigation, narrow and desktop layouts, safe error messages, secret handling, and read-only public routes.
- Finish the multi-stage production image and Compose database/migration/seed startup.
- Configure CI to lint, type-check, test, build the frontend, and build the image using frozen fixtures.

**Deliverables:** passing required checks, Docker image, Compose startup, CI workflow, and evidence record.

**Completion gate:** a fresh checkout starts with the real seed; required tests pass; restarting the application preserves the accepted database release. Ordinary CI does not depend on live Elexon availability.

**Dependencies:** Phases 1–5. **Backlog mapping:** P0-10 and P0-11. See [Phase 6 evidence](PHASE_6_STATUS.md) and [verification commands](VERIFICATION.md) for actual test, image, persistence and CI status. Remote CI runs from the eventual committed public checkout remain a publication gate.

## Phase 7 Public deployment and verification

**Objective:** make the completed pilot accessible to a logged-out reviewer.

Tasks:

- Deploy the tested application to the selected Vercel route with external PostgreSQL, after account and plan verification.
- Configure secrets, managed PostgreSQL, migrations, and the accepted January release.
- Verify HTTPS, readiness, frontend assets, date/cutoff interaction, accuracy, and CSV.
- Restart the hosted service and confirm release identity and results persist.
- Record the URL, deployed source commit, platform deployment ID, dataset release, and smoke-test result. Record the image digest when the host uses our Docker image; Vercel builds this application from source.

**Deliverables:** public application and deployment verification record.

**Completion gate:** a logged-out user can complete the analyst journey and the hosted application retains its data across restart. The rollback path and operating-cost owner are documented.

**Dependency:** Phase 6, with hosting feasibility resolved in Phase 1. **Backlog mapping:** P0-12. **Current status:** complete for the public evaluation pilot. Vercel and a separate free London PostgreSQL database are configured; a fresh logged-out browser and public HTTP/export checks passed. Replacement deployment retained the exact accepted release and result fingerprints. Free edge rules, cost ownership, recovery procedure and operational limits are recorded in [Phase 7 status](PHASE_7_STATUS.md).

## Phase 8 Documentation demonstration and submission

**Objective:** make the work easy for the company to evaluate and reproduce.

Tasks:

- Complete README startup commands, directory map, actual application/video links, explicit AI disclosure, methodology, attribution, and limitations.
- Review the public repository and history for credentials, unrelated personal files, and assignment material that should not be published.
- Record a roughly nine-minute video: customer demonstration and technical walkthrough, each below five minutes.
- Upload the video as unlisted and verify logged-out playback.
- Check the repository, application, and video links in incognito, then complete the assignment form and retain confirmation.

**Deliverables:** reviewed public repository, reproducible README, unlisted video, checked URLs, and submission confirmation.

**Completion gate:** all mandatory assignment artifacts actually exist and are accessible. Planned links or an opened form do not count as a completed submission.

**Dependency:** Phase 7 for final verification and recording. Draft notes and the script should be written throughout earlier phases. **Backlog mapping:** P0-13 through P0-15.

**Current status:** public repository, reviewed history, README/review materials and full remote CI are verified. The user chose to record their own voice; the nine-minute script/checklist is ready. Recording, unlisted upload, final playback/link checks and company submission remain pending. See [Phase 8 status](PHASE_8_STATUS.md).

## Phase 9 Operational data reliability

**Objective:** adapt the pilot to a daily utility workflow.

Add scheduled ingestion, a single-run lock, resumable jobs, overlapping correction windows, deadline-aware source freshness and coverage monitoring, and frozen operational snapshots based on data actually received by the decision cutoff. Confirm how revised actuals and source conflicts are handled.

**Completion gate:** replay, source-outage, correction, and job-recovery exercises pass; an assigned data owner accepts the source contract and cutoff behavior.

**Dependency:** accepted pilot and confirmed client workflow. **Effort:** estimate separately after reviewing client access and operational requirements.

## Phase 10 Security access and recovery

**Objective:** establish the controls needed for a client-operated service.

Add corporate identity integration, viewer/operator roles, least-privilege database accounts, administrative audit, environment separation, approved hosting region, retention policies, automated backups, and controlled promotion/rollback. Perform a timed database restore and rollback exercise.

**Completion gate:** the client accepts access controls and operational procedures; backup and recovery objectives have measured evidence; unresolved critical security findings are closed.

**Dependency:** confirmed client security and platform requirements. This phase can overlap Phase 9 when dependencies allow. **Effort:** separately estimated.

## Phase 11 Client acceptance and production launch

**Objective:** obtain explicit approval for operational reliance.

Confirm the venue/product rules, internal cutoff, delivery boundaries, source comparison semantics, and data-quality policies. Run analyst acceptance sessions, measure the agreed performance and availability objectives, establish alert escalation and support ownership, and document operating costs and recovery procedures.

**Completion gate:** product, trading/data, security, and operations owners approve their evidence and the service has an agreed launch and support plan. Additional demand, price, or portfolio integrations remain a separately scoped extension.

**Dependencies:** Phases 9 and 10. **Effort:** separately estimated; no unsupported production launch date is promised.

## Current position and next action

Phases 1–7 and the later frontend/security enhancements are implemented. The public evaluation pilot is available at [Wind Desk](https://tme7d41m5t.vercel.app), with reviewed history in the [anonymous-name repository](https://github.com/Mayank2142/tme7d41m5t) and full remote CI verified. Complete Phase 8 by recording/uploading the required own-voice unlisted video using the [recording checklist](RECORDING_CHECKLIST.md), verifying final playback/links and submitting through the company's specified channel. Client operational use remains subject to Phases 9–11.
