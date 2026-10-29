# Phase 5 Analyst Dashboard Verification

Recorded on 29 October 2026, Asia/Calcutta.

**Status: implemented and verified locally.** The React analyst journey now runs at [127.0.0.1:8000](http://127.0.0.1:8000/), using the accepted real Elexon dataset and Phase 4 APIs. Decision, Accuracy, and Data & Methodology are functional views. Public hosting remains a later phase.

## Delivered

- Decision date and cutoff controls, following-day delivery bounds, native forecast coverage, mean/peak reported values, publication range, and age at cutoff.
- Forecast-only generation chart with pointer/keyboard inspection and a complete publication/source-record ledger.
- Accuracy date range, four server-calculated metrics, forecast/original-actual overlay, signed-error plot, daily review, largest misses, reconciled coverage, and paginated exact-value/source tables.
- Methodology/source view with generation scope, calendar and cutoff assumptions, comparison/vintage rules, formulas, quality counts, original request links/digests, and source-validation ledger.
- Shareable URLs preserving the saved decision date, accuracy range, cutoff, and explicit release across all views. Browser history restores applied selections; only relevant filters are forwarded to each API.
- Separate draft/applied controls, query keys and abort signals for changed selections, visible loading/empty/partial/unavailable/error states, and explicit failed-refresh handling.
- Downloads using the returned guarded URL, with media type/context/release verification before browser delivery. Unapplied edits, refresh failures, and in-flight refreshes disable unsettled exports.
- Semantic navigation, skip link, heading focus, labeled inputs, keyboard chart sliders, captioned/scoped data tables, named focusable scroll regions, reduced-motion support, and responsive layouts.
- Typed API clients with runtime checks and attributed frozen API fixtures for offline tests. Product code has no synthetic-data fallback and no new dependency was added.

See the [workbench guide](WORKBENCH.md), [API contract](API.md), [methodology](METHODOLOGY.md), and [interface decision](decisions/0006-analyst-interface.md).

## Tests actually run

The final frontend suite passed **43 tests across five files**, with no skipped tests, in **9.15 seconds**. Lint, TypeScript checking, and the production Vite build pass. The final build contains the full interface and native SVG charts; test fixtures are not in the production import graph.

| Test area | Cases | Evidence |
| --- | ---: | --- |
| Existing configuration boundaries | 8 | Valid data release, malformed metadata, unavailable service |
| URL and filter state | 9 | January bounds, malformed/repeated filters, pinned release/defaults, cross-view date/cutoff preservation |
| Analysis client and export contracts | 12 | Frozen real responses, context/header/filter/publication mismatch rejection, source link safety, download identity and stale-context errors |
| Analyst workflow | 12 | Draft and pending transitions, retrospective view, methodology, failures/retries, failed refresh, stale download, explicit pin switching, reset/history, no-data and partial coverage |
| Chart gap semantics | 2 | Valid zero retained, no bridge across a missing target, no fabricated all-missing zero line |

The first workflow run exposed test-selector assumptions about decorative navigation numbers, repeated cutoff labels, and one mistyped expected source value. Assertions were corrected against the real frozen response, and decorative tab numbers were hidden from accessible names. The clean suite above passed after those changes.

The Python calculation/persistence/API source tree is unchanged from Phase 4. Its **85 passing backend tests**, including four PostgreSQL integration tests, remain that phase's recorded evidence; they are not presented as a newly repeated Phase 5 run. Phase 5 additionally exercised the running PostgreSQL-backed APIs through the actual browser interface and download files. Phase 6 consolidates integrated verification and CI.

## Real-browser checks

An isolated Chrome session driven by the Playwright CLI verified:

- Default January 31 purchase decision, February 1 delivery, 24 eligible forecasts, and the real mean/peak/publication/age values.
- Changing cutoff from 09:00 to 09:45 first marks a draft and disables export; applying changes the URL, forecast values, selected issue, and age together.
- At 09:00, the February 1 midnight forecast is 10,099 MW, with the oldest issue aged 1h 30m. At 09:45 it is 10,474 MW, with the selected 09:30 issue aged 15m.
- Native Home/ArrowRight chart inspection moves to target 2, February 1 at 01:00, displaying 10,117 MW at the later cutoff and its matching publication/age.
- Full January Accuracy at 09:45 displays 744/744 pairs and the four correct rounded metrics. Daily January 1 drill-down narrows the complete analysis to 24 pairs.
- Methodology shows ten source-response links; its Accuracy return link retains the selected single-day range, cutoff, and release. Reload/history restore the applied URL.
- Desktop at 1440 pixels and mobile at 390 pixels render the real data. A 320-pixel check confirms no document overflow and all signed metric values fit their cards. Wide tables scroll inside their own named containers.
- Final browser console check reports **0 errors and 0 warnings**.

Visual review found and corrected an error-plot aspect-ratio mismatch and a six-pixel signed-bias overflow at 320 pixels. Muted text contrast was strengthened. Desktop and mobile screenshots were rendered and inspected. These local checks are not a comprehensive assistive-technology audit or a measured performance/availability guarantee.

## Actual browser downloads

The browser downloaded both files through the interface at 09:45. Their exact bytes were parsed separately and compared with a fresh live API read of the same selection:

| Download | Observed result |
| --- | --- |
| January 31 Decision CSV | 24 rows; no actual/error columns; every publication is eligible; first forecast 10,474 MW |
| Full January Accuracy CSV | 1,488 half-hour rows; 744 valid metric pairs; all four independently recomputed metrics agree with JSON |
| Release and context | Every row matches the selected API release/context; guarded URLs were used |

Recomputed Accuracy metrics in MW: MAE **1,995.5685483870968**, RMSE **2,498.8245110107187**, signed bias **+1,727.9825268817203**, P90 **4,183.9**. These are the later-cutoff source-time results, not future uncertainty bounds or procurement recommendations.

The source release remains `f61cecb1c14d91cfc32f10c74a9945fd2cf7f1851abd8ca6b0eb3f3e8975b052`. No source re-download, migration, paid resource, remote repository, or public deployment was created in this phase.

The [machine evidence](phase-5-evidence.json) records response/download/context fingerprints, fixture/build/source hashes, measured work window, and check results. Local screenshots and actual downloads are under ignored `output/playwright/` and `.playwright-cli/` directories. They are verification artifacts, not application startup dependencies.

## Next phase

Phase 6 completes the integrated quality gate: repeat the critical seeded user journey as part of reproducible checks, finish Docker/Compose execution, configure CI, and review the remaining public-release controls. Docker's Linux engine and external Vercel/PostgreSQL readiness retain their earlier unresolved status until verified. Operational utility acceptance remains separately scoped.
