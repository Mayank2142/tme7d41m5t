# Implementation Backlog and Acceptance Evidence

Use this backlog with the [implementation plan](../IMPLEMENTATION_PLAN.md). Phases 1–7 are implemented and verified for the public historical pilot; Phase 8 has published the anonymous-name source repository and records actual remote execution in [its status/evidence](PHASE_8_STATUS.md). The required own-voice unlisted video and final submission remain outstanding. The research report does not substitute for application checks. Actual cumulative effort against the sixteen-hour assignment limit has not been fully reconciled.

Follow [Project phases](PROJECT_PHASES.md) for the execution order, effort allocations, and phase completion gates. The P0 identifiers below map to those phases.

## Mandatory work items

| ID | Work item | Depends on | Completion evidence |
| --- | --- | --- | --- |
| P0-01 | Confirm source schema, January mapping, comparison policy, and hosting route | None | Pilot policies recorded; Vercel account and separate Neon Free database verified; no paid upgrade enabled; operational commercial use requires separate approval |
| P0-02 | Bootstrap API, React, database, and quality tools | P0-01 policies | Local and hosted browser/API connections, configuration and PostgreSQL verified; see Phase 7 |
| P0-03 | Implement raw archive and versioned persistence | P0-02 | Verified in Phase 2: PostgreSQL migrations, immutable evidence, duplicate-safe import, frozen membership, archive recovery |
| P0-04 | Backfill required January decision data and produce seed | P0-03 | Verified in Phase 2: real seed, accepted release, full coverage, source manifest, and persisted readiness |
| P0-05 | Implement calendar and latest eligible source-key selection | P0-03 | Verified in Phase 3: local calendar, inclusive cutoff, mixed issues, latest invalid/conflict, no later decision evidence |
| P0-06 | Implement source-time comparison, metrics, and coverage ledger | P0-05 | Verified in Phase 3: hand arithmetic, all ledger states, null no-pair metrics, pooled ranges, independent real-source checks |
| P0-07 | Implement read APIs, analysis context, and export | P0-04, P0-06 | Verified in Phase 4: typed filters/results, forecast-only Decision, canonical contexts, pinned quality/CSV, independent export metric recomputation, real PostgreSQL reads |
| P0-08 | Implement Decision view | P0-07 | Verified Phase 5: real native forecasts, January/February boundary, draft/applied cutoff, publication/age/coverage, keyboard inspection and exact source table |
| P0-09 | Implement Accuracy and Methodology views | P0-07 | Verified Phase 5: metrics/coverage, original half-hour actuals, signed errors, daily/large-miss review, method/provenance, shared filters, guarded downloads |
| P0-10 | Complete integration and browser verification | P0-08, P0-09 | Latest 107 backend/47 frontend tests, independent CSV arithmetic and actual logged-out browser journeys, keyboard and 320/390/1440-pixel layouts; Phase 8 corrects clean-runner test isolation assumptions |
| P0-11 | Finish Docker startup and CI | P0-02, P0-10 | Local startup and isolated image/seed/browser/restart gates verified; actual Linux job results and immutable commit links recorded in Phase 8 |
| P0-12 | Deploy accepted release and verify durability | P0-11 | Verified public HTTPS, readiness, context/export and accepted-release persistence across application replacement; see Phase 7 |
| P0-13 | Complete README, attribution, architecture and operations handoff | P0-12 | Startup and directory map, source attribution, AI disclosure, architecture/code map and operator guide included; actual video link depends on P0-14 |
| P0-14 | Record customer and technical demonstration | P0-12, P0-13 | **Pending user recording:** own-voice script/checklist prepared; final unlisted video, ≤10-minute duration and audio/playback checks required |
| P0-15 | Verify public artifacts and submit | P0-14 | Public app/source and anonymous clone checked; **pending** video, final link checks and actual company submission confirmation |

At roughly four hours, require P0-04 through P0-06 as a working data/domain spike. At eight hours, require a working analyst journey through the core APIs and UI. At twelve hours, stop optional work and require the core deployment so the remaining time protects fixes and submission artifacts. Resolve hosting access during P0-01, not at P0-12.

## Optional work only after the required journey

| ID | Enhancement | Acceptance condition |
| --- | --- | --- |
| P1-01 | Previous eligible forecast revision overlay | Never compares with a post-cutoff issue; publication identities visible |
| P1-02 | WAPE and detailed delivery-hour analysis | Zero denominator is null; sample count and comparison policy explicit |
| P1-03 | Hourly-mean sensitivity view | Both actual components required; interval assumption labeled; separate metrics |
| P1-04 | Prior-outcome historical context | Actual publication bounded by decision cutoff; insufficient history represented |

Do not make video or deployment completion depend on these items. Forecasting models, probabilistic procurement buffers, price analysis, and portfolio integration require a new scope.

## Mandatory integrity acceptance examples

**Latest source key:** a target has a valid 07:30 issue and conflicting 08:30 records. At 09:00, the target is marked invalid under the default policy. The application must not silently choose 07:30 by filtering invalid rows before selecting the latest key.

**No hindsight:** a forecast issued at 09:30 cannot appear in the 09:00 decision view. Future actual values and monthly hindsight cards are absent from its API response as well as its visible UI.

**Comparison:** for the verified midnight 2 January example, the 09:00 selected forecast is 18,781 MW and the equal-timestamp actual is 15,228 MW, giving +3,553 MW under `source_timestamp_v1`. The separately labeled hourly-mean interpretation gives a different result and cannot share its metric identifier.

**Missing data:** deleting one paired actual from a fixture produces one unpaired target, a lower paired coverage count, and a visible reason. It does not create zero generation or silently shrink the denominator.

**Release consistency:** while the operator activates a new dataset release, a user holding the earlier release obtains the same earlier chart and CSV. A refresh can explicitly select the new release. An old release's members and validation outcomes stay immutable.

**Recovery:** a malformed source batch cannot replace an accepted release. After an application restart, the accepted database release and its results remain available. A previous compatible release can be reactivated without deleting source evidence.

## Release evidence register

Populate this register during implementation; an empty entry means the check is outstanding.

| Evidence | Where to record it | Status |
| --- | --- | --- |
| Final decision and comparison policies | Methodology and decision records | Implemented pilot rules in `METHODOLOGY.md`; operational client approval outstanding |
| Actual-effort log | Repository work log | Recorded work windows; earlier exact effort remains unknown and is not invented |
| Accepted real-data release and manifest | Seed/archive and data-quality report | Verified Phase 2; same release used for Phase 3 calculations |
| Domain, integration, and browser results | CI run and local verification record | Latest 107 backend/47 frontend tests; source-independent CSV checks and actual browser journeys; public Linux execution recorded in Phase 8 |
| Source data attribution confirmed | README and attribution file | Verified Phase 2 and included in source/analysis artifacts |
| Application commit and image digest | Release notes | Local image evidence retained; Phase 7 records actual Vercel source/deployment IDs (Vercel builds from source); CI records its image revision and persistence checks |
| Public application and restart check | Deployment record | Verified in Phase 7; accepted release and fingerprints unchanged across replacement deployment |
| Fresh Docker startup | Handoff verification record | Verified from committed checkout and retained local evidence, including seed, browser/CSV, replay/restart, separate-database restore and Desktop recovery |
| Public repository and actual README links | Submission checklist | Published and anonymously cloned; app/source/guide links checked without cookies or Authorization |
| Unlisted video and duration | Submission checklist | Pending own-voice recording, upload and measured duration |
| Incognito access and form confirmation | Submission checklist | App/source access verified; video and final company confirmation pending |

No URL, test pass, deployment identifier, or completion status should be invented to fill the register. The final handoff explains any outstanding item and its practical effect.
