# Read API and CSV Contract

Implemented in Phase 4. Start the seeded local service and open [interactive API documentation](http://127.0.0.1:8000/api/docs). The machine-readable contract is available at `/api/openapi.json`. Documentation endpoints default off in production. All application reads use stored Elexon data; ordinary requests do not trigger downloads or ingestion.

The public read API has per-process rate/admission limits and request-size/host checks. Rejected traffic receives safe JSON errors; 429 and overload 503 include `Retry-After`. Immutable analysis serialization is cached internally while responses retain `Cache-Control: no-store`. Accepted release lookup and export context checks remain live on cache hits. See [security and scaling](SECURITY_AND_SCALING.md) for limits and the required hosting controls.

## Routes and filters

| GET route | Filters | Result |
| --- | --- | --- |
| `/api/v1/config` | None | Pilot scope, configured cutoff, supported comparison policy, calculation versions, and current dataset status |
| `/api/v1/decision-view` | Required `decision_date`; optional `cutoff_local`, `release_id` | Forecast-only decision replay |
| `/api/v1/accuracy` | Required `decision_from`, `decision_to`; optional `cutoff_local`, `comparison_policy`, `release_id` | Retrospective daily and pooled accuracy, target ledger, and original half-hour observations |
| `/api/v1/data-quality` | Optional `release_id` | Typed validation report and original-response provenance for one accepted release |
| `/api/v1/export.csv` | Required `mode`; matching decision or accuracy filters; optional `expected_context_id` | Exact selection with source keys, context, and coverage states |
| `/health/live` | None | Process liveness |
| `/health/ready` | None | Database and accepted-release readiness |

Dates use `YYYY-MM-DD` and must be January 2026 purchase decision dates. Accuracy ranges are inclusive and ordered; the largest range is thirty-one days. January 31 concerns all of February 1 delivery. Cutoff uses a real local `HH:MM` minute in Europe/London, with no seconds or offset; omission resolves the configured default, currently 09:00. The cutoff remains illustrative.

Only `source_timestamp_v1` is supported. A release ID is a complete lowercase SHA-256 identifier. Omitting it selects the current accepted release once. Explicit unknown or rejected IDs return 404. Unsupported parameters, duplicate parameters, timestamp-like dates, unsupported policies, invalid cutoffs, and incompatible export-mode filters are rejected rather than silently ignored.

Decision export requires `mode=decision` and `decision_date`, and rejects accuracy-range/comparison filters. Accuracy export requires `mode=accuracy`, `decision_from`, and `decision_to`, and rejects `decision_date`. Its omitted comparison policy resolves to `source_timestamp_v1`.

Examples:

```text
/api/v1/decision-view?decision_date=2026-01-31&cutoff_local=09:00
/api/v1/accuracy?decision_from=2026-01-01&decision_to=2026-01-31&cutoff_local=09:00&comparison_policy=source_timestamp_v1
/api/v1/export.csv?mode=decision&decision_date=2026-01-31&cutoff_local=09:00
```

## Response envelope and context

Decision and Accuracy have distinct typed response schemas:

| Field | Meaning |
| --- | --- |
| `analysis_context_id` | Deterministic identifier for this release, filters, mode, policies, resolutions, and application build |
| `context` | The complete normalized inputs used to calculate the identifier |
| `analysis` | Typed domain result: window/points/coverage/summary for Decision; days/metrics/coverage/actual observations for Accuracy |
| `source` | Dataset endpoints, attribution, licence, and a quality-report URL pinned to this release |
| `export_url` | Relative CSV URL carrying the resolved filters, explicit release, and expected context ID |

`analysis_context_v1` hashes the UTF-8 JSON serialization of `context`, with sorted keys, compact separators, and `ensure_ascii=false`, using SHA-256. No request timestamp, active-pointer activation time, or URL parameter order is included. The resolved cutoff is included, so an explicit default and an omitted default yield the same context.

Common context inputs include mode, release, source parser, date bounds, cutoff, timezone, calendar/selection/availability policies, forecast cadence, application version, and build identifier. Accuracy adds comparison policy, actual-vintage rule, actual interval, and metric version. Decision has no retrospective fields.

Follow the returned `export_url` to preserve the analysis shown on screen. The export resolves that explicit release, recomputes through the same application service, and checks `expected_context_id`. If filters or the application build changed, it returns 409 rather than a misleading download. A direct export without this guard is also supported and describes its own resolved context. Requests do not persist context objects or mutate the dataset.

`GRID_BUILD_SHA` is `local` in this development workspace. A deployed build must set its real source commit identifier as part of release verification. The context is a reproducibility identifier, not an authentication token, source signature, or proof that different unversioned local code is identical.

All successful JSON analysis responses and CSV downloads return `X-Analysis-Context-ID` and `X-Dataset-Release`. `X-Request-ID` identifies every response, and API/health responses use `Cache-Control: no-store`. Public JSON timestamps serialize in UTC with `Z`. CSV also includes an offset-bearing London target timestamp.

## Forecast and retrospective boundaries

The Decision service loads only forecast members. It returns every expected native target with eligible selected publication/version IDs, generation or null, reason, and age at cutoff. Its coverage counts valid/missing/invalid forecasts. Its summary describes reported native target values, without treating them as a proven energy profile. It contains no actual values, source-actual metadata, errors, or retrospective metrics.

Accuracy selects those same forecasts and compares them with the latest valid source key in the frozen actual release. Its response explicitly labels retrospective use and source-time comparison. There are 744 expected hourly comparison targets and 1,488 separate half-hour actual targets for the complete range. Both daily and pooled range results preserve missing/invalid states. See [methodology](METHODOLOGY.md) for rules and interpretation.

Quality responses retain the existing `payload_sha256` name for original-response digests. The portable archive manifest separately calls that field `sha256`; these are different serialization contracts. A legacy quality report without the newer normalized-version fingerprint returns null for that optional fingerprint rather than inventing one. Raw payload bodies and database configuration are absent.

## CSV layout and recomputation

CSV uses UTF-8, a header row, CRLF record endings, standard CSV escaping, and an attachment filename derived from validated mode/date/context fields. Exports are bounded by the January filter contract and assembled before sending the response, so a failed read cannot deliver an apparently successful partial file.

Decision has one row per native forecast target: 24 for a January decision. Its columns contain forecast data, window, cutoff, age, source-version IDs, release/context/build/policy metadata, and attribution. Actual and error columns do not exist in that export.

Accuracy has one row per expected half-hour target: 48 per delivery day, or 1,488 for the full range. This preserves all the actual observations available to the chart without double counting comparison points:

| `row_type` | Count in a complete month | Interpretation |
| --- | ---: | --- |
| `comparison_target` | 744 | Native forecast target and equal-timestamp actual; `comparison_expected=true` |
| `actual_only` | 744 | Intervening half-hour actual; no synthetic forecast or error; `comparison_expected=false` |

`used_in_metrics=true` only when both values at a comparison target are valid. Recompute metrics from those rows' numeric `error_mw`. Positive means overforecast. `absolute_error_mw` is included. Sum the five `evaluation_state` categories across comparison targets to reconstruct the ledger; include missing/invalid comparison rows in the expected denominator. `actual_state` across all rows reconstructs separate half-hour source coverage.

Null or inapplicable numeric cells are empty; valid zero is `0`. Actual-only forecast and error cells remain empty. Publication, source-version IDs, and per-source quality reasons remain available for invalid selected keys. Version-ID cells contain JSON arrays, preserving conflicting-key evidence without delimiter ambiguity.

Textual cells beginning with spreadsheet formula prefixes are neutralized with a leading apostrophe, including prefixes after leading whitespace. This does not alter legitimate numeric negative errors. Quoted commas, quotation marks, and line breaks use the CSV writer's normal escaping. The required BMRS attribution and licence accompany every row.

## Errors and observability

New read routes use this envelope:

```json
{
  "code": "INVALID_FILTERS",
  "message": "Check the supplied query filters.",
  "request_id": "<same identifier as X-Request-ID>",
  "errors": [{"field": "query.cutoff_local", "code": "value_error", "message": "<validation explanation>"}]
}
```

The example uses placeholders for request-specific identifiers. Invalid filter values and database exception contents are not echoed. Error responses remain JSON when requested through a CSV route.

| Status | Code examples | Meaning |
| --- | --- | --- |
| 200 | None | Valid request, including missing-data results with explicit nulls and coverage |
| 404 | `RELEASE_NOT_FOUND`, `NOT_FOUND` | Unknown/rejected release or unknown route |
| 405 | `METHOD_NOT_ALLOWED` | Unsupported HTTP method |
| 409 | `ANALYSIS_CONTEXT_MISMATCH` | Download does not match the expected analysis context |
| 422 | `INVALID_FILTERS`, `DUPLICATE_FILTER` | Invalid, unsupported, missing, or ambiguous filters |
| 429 | `RATE_LIMITED` | Per-process API backstop reached; `Retry-After` gives the wait in seconds |
| 503 | `NO_ACCEPTED_DATASET`, `DATABASE_UNAVAILABLE`, `SCHEMA_NOT_INITIALIZED` | Stored data cannot currently serve the request |
| 500 | `INTERNAL_ERROR` | Unexpected failure with no internal details in the response |

Readiness retains its dedicated health-state schema. The operator server emits structured request records with request ID, route, status, duration, error code, release, and analysis context when available. It omits query strings, credentials, and source payloads. API routes are read-only; ingestion remains in the operator CLI.

Phase 6 adds a bounded direct-peer API quota, safe errors, browser security headers and verified local container execution; see [verification](VERIFICATION.md). Host-level shared quotas/proxy identity, concurrent-load measurements and hosted verification remain deployment/operational checks. No achieved latency or availability objective is claimed.
