# Wind Forecast Decision Support Project Brief

Proposed assignment delivery · 29 October 2026

Implementation update: the real-data pipeline, calculation engine, typed APIs/CSV and three-view React interface are implemented and deployed at [Wind Desk](https://tme7d41m5t.vercel.app). The [public source](https://github.com/Mayank2142/tme7d41m5t) has an anonymous repository name. [Phase 7 evidence](PHASE_7_STATUS.md) records 107 backend and 47 frontend tests, PostgreSQL checks, independent CSV arithmetic, logged-out browser journeys and hosted replacement persistence. At 09:00, all 744 source-time targets pair, with MAE 2,022.47 MW. Pinned links preserve dates, cutoff, release and download context. Remote CI is being verified. The required own-voice unlisted video and final submission remain outstanding; this is not operational utility acceptance.

This project gives a UK utility's procurement team a clear view of the Elexon wind forecast available before a day-ahead purchase decision and a reproducible assessment of its historical error. The assignment requires a deployed React/Python application, Docker setup, public source and a short customer/technical demonstration. The original sixteen-hour total-effort limit remains part of the brief; cumulative actual effort has not been fully reconciled.

## Business value

An analyst will select a January 2026 decision date and desk cutoff, inspect the following day's wind outlook, see when each forecast was published, and identify missing or older information. A retrospective view will quantify the error using MAE, RMSE, signed bias, P90 absolute error, and paired coverage. CSV exports will carry the same filters and source identifiers as the screen.

The product supports judgment about wind uncertainty. A utility-specific purchase recommendation needs demand, existing positions, contracted renewable entitlement, and prices, which the assignment does not supply. The proposal therefore makes no unsupported savings or trading-profit claim.

## Evidence informing the design

Planning research checked all thirty-one January decision dates against Elexon's public WINDFOR and FUELHH streams. It found 744 of 744 expected native forecast targets at each of two tested cutoffs, 09:00 and 09:45 GMT, with matching actual timestamps, and all 1,488 required actual half-hours. No null generation, negative generation, duplicate rows, or conflicting keys were found in those retrieved responses. Request hashes and daily coverage are retained in the [research report](research/elexon_verification.json).

The planning report establishes feasibility and observed source coverage. Implementation and test evidence are recorded separately in the phase status documents; neither constitutes operational certification. Source forecasts have hourly target timestamps while actuals are half-hourly. The implemented engine compares equal source timestamps as described in the brief; a full-hour averaging interpretation, if included, will be separately labeled.

January is interpreted as the month of purchase decisions. Consequently, required delivery dates run from 2 January through 1 February. The default 09:00 Europe/London cutoff is a visible illustrative desk assumption, and can be changed; the client's actual venue and operational cutoff require confirmation.

## Proposed implementation

React with TypeScript provides the portal and FastAPI provides the Python service, with PostgreSQL storing source revisions and immutable dataset releases. Docker provides a reproducible local application. The verified Vercel deployment serves compiled React and the API from one origin, backed by a separate Neon Free PostgreSQL database in London. The function uses a restricted reader and verified TLS; the selected free plans have no paid upgrade enabled. [Deployment status](PHASE_7_STATUS.md) records the scope, cost ownership and operational limits.

Source ingestion runs separately from user requests. Forecasts are selected by publication time for each target, and all results include release, policy, and source provenance. A failed refresh preserves the previous accepted release. The public pilot has read-only routes and public source data; administrative ingestion remains an operator command.

## Acceptance evidence

The submission will demonstrate:

- A cutoff change that selects the correct historical issue and never introduces a later forecast into an earlier decision.
- Explicit treatment of hourly forecasts, half-hour actuals, missing values, and error direction.
- Metrics that reproduce from an export under the recorded comparison policy.
- A fresh Docker startup, passing critical tests, working public HTTPS application, and persistence after restart.
- A readable public repository, precise README with AI disclosure, and a playable unlisted video under ten minutes.

Application, data, local/container and hosted verification evidence exist. Repository publication is complete, remote CI is being verified, and the recording is prepared in the [script](DEMO_SCRIPT.md) and [checklist](RECORDING_CHECKLIST.md). The mandatory video and final submission are incomplete until actual artifacts and confirmation exist.

## Delivery and production path

The [implementation plan](../IMPLEMENTATION_PLAN.md) allocates the sixteen-hour total across source verification, core implementation, testing, deployment, documentation, video, submission, and contingency. Optional analyses are cut before the mandatory demonstration or correctness checks. Research already performed counts toward that effort.

Before operational utility use, complete domain sign-off, scheduled ingestion and receipt-aware decision snapshots, corporate identity and access controls, backup/restore and rollback exercises, measured performance, monitoring, support ownership, and analyst acceptance. Estimate that work after the pilot and client dependency review. The assignment demonstrates a sound engineering foundation and makes the remaining operational work reviewable.
