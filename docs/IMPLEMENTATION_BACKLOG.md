# Implementation Backlog and Acceptance Evidence

Use this backlog with the [implementation plan](../IMPLEMENTATION_PLAN.md). Phases 1–5 are implemented locally; Phase 6 consolidates the real-data journey, tests, packaging, image checks and CI. [Phase 6 status](PHASE_6_STATUS.md) distinguishes local verification from pending remote gates. The research report does not substitute for application checks. Record real elapsed effort, including research, against the sixteen-hour assignment limit.

Follow [Project phases](PROJECT_PHASES.md) for the execution order, effort allocations, and phase completion gates. The P0 identifiers below map to those phases.

## Mandatory work items

| ID | Work item | Depends on | Completion evidence |
| --- | --- | --- | --- |
| P0-01 | Confirm source schema, January mapping, comparison policy, and hosting route | None | Policies recorded; user selected Vercel; account, database, and budget verification outstanding |
| P0-02 | Bootstrap API, React, database, and quality tools | P0-01 policies | Local browser/API connection, configuration, tools, and live PostgreSQL verified; external hosting remains separate |
| P0-03 | Implement raw archive and versioned persistence | P0-02 | Verified in Phase 2: PostgreSQL migrations, immutable evidence, duplicate-safe import, frozen membership, archive recovery |
| P0-04 | Backfill required January decision data and produce seed | P0-03 | Verified in Phase 2: real seed, accepted release, full coverage, source manifest, and persisted readiness |
| P0-05 | Implement calendar and latest eligible source-key selection | P0-03 | Verified in Phase 3: local calendar, inclusive cutoff, mixed issues, latest invalid/conflict, no later decision evidence |
| P0-06 | Implement source-time comparison, metrics, and coverage ledger | P0-05 | Verified in Phase 3: hand arithmetic, all ledger states, null no-pair metrics, pooled ranges, independent real-source checks |
| P0-07 | Implement read APIs, analysis context, and export | P0-04, P0-06 | Verified in Phase 4: typed filters/results, forecast-only Decision, canonical contexts, pinned quality/CSV, independent export metric recomputation, real PostgreSQL reads |
| P0-08 | Implement Decision view | P0-07 | Verified Phase 5: real native forecasts, January/February boundary, draft/applied cutoff, publication/age/coverage, keyboard inspection and exact source table |
| P0-09 | Implement Accuracy and Methodology views | P0-07 | Verified Phase 5: metrics/coverage, original half-hour actuals, signed errors, daily/large-miss review, method/provenance, shared filters, guarded downloads |
| P0-10 | Complete integration and browser verification | P0-08, P0-09 | Verified Phase 6: 90 backend tests including five PostgreSQL tests; 43 frontend tests; independent CSV arithmetic and real-browser journey/downloads; keyboard and narrow-layout checks |
| P0-11 | Finish Docker startup and CI | P0-02, P0-10 | Pinned image and isolated image/seed/browser/restart gate; local outcome in Phase 6 status; workflow passes actionlint; remote run awaits the public committed repository |
| P0-12 | Deploy accepted release and verify durability | P0-11 | HTTPS, readiness, source context, export, and restart persistence checked |
| P0-13 | Complete README, attribution, architecture and operations handoff | P0-12 | Another developer follows startup; source rights checked; AI tools disclosed |
| P0-14 | Record customer and technical demonstration | P0-12, P0-13 | Unlisted video below ten minutes; each part below five; audio and links checked |
| P0-15 | Verify public artifacts and submit | P0-14 | Incognito checks, exact release commit, actual form confirmation |

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
| Domain, integration, and browser results | CI run and local verification record | Phase 6: 90 backend and 43 frontend tests, independent service/CSV checks, actual browser journey/downloads, keyboard and narrow-layout checks pass; remote CI awaits publication |
| Source data attribution confirmed | README and attribution file | Verified Phase 2 and included in source/analysis artifacts |
| Application commit and image digest | Release notes | Planned |
| Public application and restart check | Deployment record | Planned |
| Fresh Docker startup | Handoff verification record | See Phase 6 status for clean-source image, seed and persistence evidence; a fresh committed checkout remains a publication check |
| Public repository and actual README links | Submission checklist | Planned |
| Unlisted video and duration | Submission checklist | Planned |
| Incognito access and form confirmation | Submission checklist | Planned |

No URL, test pass, deployment identifier, or completion status should be invented to fill the register. The final handoff explains any outstanding item and its practical effect.
