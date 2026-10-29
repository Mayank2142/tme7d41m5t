# Phase 4 Read APIs and Export Verification

Recorded on 29 October 2026, Asia/Calcutta.

This is the Phase 4 historical record. [Phase 5](PHASE_5_STATUS.md) subsequently connects the React analyst views and verifies their real browser/download behavior.

**Status: implemented and verified locally.** The accepted PostgreSQL release now serves typed Decision, Accuracy, and quality endpoints plus consistent CSV. The local API documentation is available at [127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs). The React overview still shows source readiness; the analyst interface is Phase 5 work.

## Delivered

- Explicit January-date, ordered-range, local-minute cutoff, accepted-release ID, policy, and export-mode validation. Unknown and repeated filters are rejected before source reads.
- Distinct forecast-only Decision and retrospective Accuracy response contracts. Decision does not load actuals or return retrospective fields.
- Shared application services over the Phase 3 engine, resolving one accepted release before reading its immutable members.
- Canonical `analysis_context_v1` identifiers covering effective filters, mode, release, parser, applicable policies/resolutions, and application build.
- Pinned quality and download URLs; guarded downloads return 409 when the expected context differs.
- CSV retaining every expected target, source publications/version IDs, nulls, reason codes, context, attribution, and offset-bearing local timestamps. Formula-prefixed text is neutralized while numeric negative errors remain numeric.
- Typed data-quality responses, optional explicit release selection, source digest compatibility, safe JSON errors, request identifiers, and structured request metadata.
- Updated OpenAPI contract, configuration capability/version fields, [API guide](API.md), and [design decision](decisions/0005-analysis-api-and-export.md).

## Results against the accepted source release

The active release is unchanged: `f61cecb1c14d91cfc32f10c74a9945fd2cf7f1851abd8ca6b0eb3f3e8975b052`, parser `elexon_streams_v2`. No upstream re-fetch or migration was required.

Live HTTP checks verified:

| Check | Observed result |
| --- | --- |
| January 31 Decision JSON and CSV | 200; 24 eligible forecast targets for February 1; no actual/error fields |
| Full January Accuracy JSON and CSV at 09:00 | 200; 744 of 744 valid paired comparison targets |
| Full Accuracy CSV observation rows | 1,488, including 744 explicitly unscored intervening half-hours |
| CSV recomputation of MAE/RMSE/bias/P90 | Matches JSON within relative tolerance `1e-12` |
| Source-time metrics, MW | MAE 2,022.470430107527; RMSE 2,497.407157584179; bias +1,745.9381720430108; P90 4,154.4 |
| Pinned quality URLs from both analyses | 200; same accepted release and ten source-response provenance entries |
| Invalid/reversed/duplicate filters | 422 with stable error code and matching body/header request ID |
| Unknown explicit release | 404 `RELEASE_NOT_FOUND` |
| Wrong expected download context | 409 `ANALYSIS_CONTEXT_MISMATCH` |
| Unknown API route | JSON 404 `NOT_FOUND` |
| Readiness, configuration, OpenAPI, API docs, frontend root | 200 |

All successful analysis/download responses carry matching `X-Analysis-Context-ID` and `X-Dataset-Release`. Independent canonical hashing reproduces the returned context IDs. API responses are not cached. The [machine evidence](phase-4-evidence.json) records full identifiers and response/download fingerprints.

These remain retrospective descriptive results under `source_timestamp_v1`, with hourly forecast timestamps and half-hour actual averages. They do not establish a calibrated forecast interval, procurement volume, savings, final settlement truth, or operational client acceptance.

## Checks actually run

The clean complete backend run passed **85 tests**, including all **four real PostgreSQL integration tests**, with no skips, in **154.37 seconds**. It retains the earlier ingestion/domain checks and adds thirty API/CSV/integration cases. The frontend passed **8 tests**, lint, type checking, and its production build. Python lint/format and the offline dependency-lock check pass.

API/export checks cover:

- Exact agreement of JSON and CSV values, selected source IDs/publications, signed/absolute errors, units, context, target counts, and all four recomputed metrics.
- No actual queries or outcomes in Decision; explicit nulls and coverage for missing data; preservation of invalid latest-key evidence; legitimate negative numeric errors.
- Context equivalence for omitted versus explicit effective defaults, sensitivity to dates/cutoff/mode/build, and stale-build download rejection.
- An active release changing during a request, with both source reads still pinned to the original release; an original export link remaining consistent after activation changes.
- Date/cutoff/policy/release/mode rejection, duplicate filters, unknown/no-active release, missing schema, unavailable database, and safe unexpected errors.
- Quality typing/provenance, unsupported HTTP methods, distinct OpenAPI schemas, CSV content declaration, text escaping, and formula-prefix protection.
- Real PostgreSQL JSON/CSV/quality reads and metric recomputation, February delivery boundary, rejection of a rejected release, and unchanged ingestion-run counts across public reads.

Integration verification found a genuine field-name mismatch: the archive manifest uses `sha256`, while the existing quality API and database adapter use `payload_sha256`. The response model and test fixture were corrected to retain API compatibility. A broad test assertion was also corrected to allow safe digest metadata while still excluding raw payload bodies. The final full run above passed after both corrections. Earlier failed attempts and reruns remain part of the work log.

## Reproduce

With PostgreSQL seeded and the web service running:

```text
GET /api/v1/decision-view?decision_date=2026-01-31&cutoff_local=09:00
GET /api/v1/accuracy?decision_from=2026-01-01&decision_to=2026-01-31&cutoff_local=09:00
```

Follow each response's `export_url` and `source.data_quality_url`. Recompute metrics only from Accuracy CSV rows with `used_in_metrics=true`; classify expected comparison coverage using `comparison_expected=true`. Other half-hour observations are retained without creating extra forecasts. See [API documentation](API.md) for exact columns and error behavior.

The full backend suite uses `GRID_TEST_DATABASE_URL` as documented in the README. PostgreSQL tests operate in isolated random schemas and remove them afterwards. Local live-response samples and downloads are retained under ignored `output/phase-4-http/`; checked-in machine evidence contains their fingerprints without depending on that ignored directory for normal startup.

## Remaining boundaries and next phase

The development build identifier is `local`; deployment must supply a real source commit. No public application, repository, or paid resource was created. Docker image/Compose execution, authenticated Vercel/external PostgreSQL setup, ingress limits, concurrent-load measurements, CI, and the final analyst browser journey remain open release checks.

Phase 5 implements React Decision, Accuracy, and Methodology screens with URL filters, loading/empty/partial/error states, accessible charts/tables, and downloads that preserve the returned release/context. The available APIs supply the real data for that work.
