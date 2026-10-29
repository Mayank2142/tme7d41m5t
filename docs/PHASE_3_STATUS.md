# Phase 3 Forecast Selection and Accuracy Verification

Recorded on 29 October 2026, Asia/Calcutta.

This is the Phase 3 historical record. [Phase 4](PHASE_4_STATUS.md) subsequently adds typed APIs, guarded CSV, and further verification.

**Status: implemented and verified locally.** The calculation engine runs against the accepted PostgreSQL release and the frozen source archive. The operator can reproduce full January results with the CLI. Public analysis APIs, CSV, and dashboard interaction follow in Phases 4 and 5.

## Delivered

- London civil-day boundaries, inclusive January decision ranges, exclusive delivery ends, and strict local-minute cutoff parsing.
- Shared domain source facts and latest-key selection used by ingestion validation and analysis. Existing parser and release identities are preserved.
- Forecast-only decision results with selected publications/version IDs, age, coverage, and reported-value summaries. Post-cutoff evidence and retrospective outcomes are absent.
- Retrospective actual selection using the latest publication within a frozen accepted release, with explicit invalid-latest behavior.
- Equal-source-timestamp pairing, four versioned metrics, daily and pooled range results, and a mutually exclusive coverage ledger.
- Separate half-hour actual observations, source coverage, and an explicit flag identifying actual points used in metrics.
- A PostgreSQL-to-domain adapter that pins one accepted release, rejects unknown/rejected IDs, and preserves old source identities while another release is active.
- `winddesk analyze`, full local JSON reports, and a compact [real-data analysis record](research/january_2026_analysis.json).

See [methodology](METHODOLOGY.md) and the [architecture decision](decisions/0004-forecast-accuracy.md) for exact rules and their limits.

## Observed January results

Both reports use January purchase decisions, following-day delivery through 1 February, the same frozen Elexon release beginning `f61cecb1c14d`, `source_timestamp_v1`, and `metrics_v1`. Values below are rounded for reading; the JSON record retains calculation precision.

| Measure | 09:00 GMT | 09:45 GMT |
| --- | ---: | ---: |
| Expected / paired targets | 744 / 744 | 744 / 744 |
| MAE, MW | 2,022.47 | 1,995.57 |
| RMSE, MW | 2,497.41 | 2,498.82 |
| Signed bias, MW | +1,745.94 | +1,727.98 |
| P90 absolute error, MW | 4,154.40 | 4,183.90 |
| Actual half-hours valid / expected | 1,488 / 1,488 | 1,488 / 1,488 |

Positive error means wind was overforecast. These are retrospective descriptive results for source values at equal timestamps. They do not resolve the hourly-forecast versus half-hour-actual interval assumption, certify final settlement data, establish a future uncertainty distribution, or quantify a utility's purchase requirement.

At midnight on 2 January, the forecast available at the 1 January 09:00 cutoff is 18,781 MW, published at 07:30. The equal-timestamp actual is 15,228 MW, published at 00:30 on 2 January. The reported error is **+3,553 MW**. That future actual appears only in retrospective analysis.

## Checks actually run

The complete backend suite passed **55 tests**, including all three real PostgreSQL integration tests with no skips, in 212.68 seconds. This adds 32 domain/frozen-source cases and one integration case to the Phase 2 suite, while extending the original persistence test to verify pinned analysis identities.

Evidence includes:

- Hand-calculated symmetric, asymmetric, single-pair, and zero-error metrics; interpolated P90; null metrics for zero pairs.
- Exactly-at-cutoff inclusion and one-microsecond-after exclusion, mixed issue times, missing targets, and absence of later evidence in Decision results.
- Latest null/negative/flagged forecasts, conflicting source keys, exact duplicate deduplication, and valid newer-key resolution.
- Revised actual vintages, invalid/conflicting latest actuals, and prevention of fallback to older actuals.
- All five evaluation states with forecast-first precedence, reconciled denominators, valid zero generation, and distinct actual half-hour coverage.
- Pooled range metrics with unequal daily pair counts; deterministic output under reordered/repeated exact inputs.
- January/February boundaries, both UK clock changes, scope and cutoff rejection.
- Independent raw-JSON errors and Python statistics at 00:00, 09:00, 09:45, and 23:59 across all January decisions.
- Accepted PostgreSQL release loading, full-month coverage, explicit bad/rejected release rejection, and old member identities while a reparsed release is active.
- Successful database-backed CLI reports at 09:00 and 09:45 using the same release as the bundled manifest.

Python lint/format and the offline dependency-lock check pass. The first database test attempt found the prepared PostgreSQL process stopped; restarting the existing cluster restored connectivity, after which the full suite passed. The lock check initially hit a sandbox cache permission error and passed using the workspace-owned uv cache. No data was reset or re-downloaded.

Frontend source and contracts are unchanged in this phase. Its eight tests and build were verified in Phase 2; new analysis-interface verification belongs to Phase 5. Docker runtime and cloud deployment checks remain open.

## Reproduce

With the local seeded PostgreSQL service running:

```text
uv run winddesk analyze --cutoff 09:00 --output output/analysis-0900.json
uv run winddesk analyze --cutoff 09:45 --output output/analysis-0945.json
uv run winddesk analyze --decision-from 2026-01-31 --decision-to 2026-01-31 --cutoff 09:00 --output output/january-31.json
```

Use `--release-id` with a complete accepted SHA-256 ID to reproduce an older release explicitly. Ordinary analysis does not contact Elexon. JSON output contains all selected evidence and original half-hour observations; CSV and public analysis context IDs remain Phase 4 work.

For the complete backend test run, set `GRID_TEST_DATABASE_URL` as described in the README. The tests create and remove isolated random schemas. The checked-in [machine evidence](phase-3-evidence.json) records test results, source/report fingerprints, observed metrics, and the measured work window.

## Next phase

Phase 4 exposes typed Decision and Accuracy endpoints, validates public filters, generates a reproducible analysis context, and exports matching CSV. The existing local overview continues to show source readiness until the analysis UI is implemented.
