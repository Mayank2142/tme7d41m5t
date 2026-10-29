# Forecast Selection and Accuracy Methodology

Implemented for the assignment pilot on 29 October 2026. This describes the calculation engine. Phase 4 exposes it through [typed read APIs and consistent CSV](API.md); dashboard controls follow in Phase 5.

## Calendar and availability

January means purchase decision dates, 1–31 January 2026 in `Europe/London`. Each decision concerns the following UK civil day. Delivery therefore spans 2 January through the end of 1 February, using an exclusive end at midnight on 2 February. The default 09:00 cutoff is illustrative and may be changed to another local minute. It is not a verified auction gate closure.

Both delivery midnights are constructed in London time and converted to UTC independently. The reusable calendar handles 23-hour and 25-hour clock-change days; the assignment's decision range remains January only. Forecast targets are hourly; the separate actual observation grid is half-hourly.

Historical availability uses the source `publishTime`, inclusively at the cutoff, under `source_publication_time`. October retrieval timestamps prove when this project downloaded the records, not that a trading desk received them in January. Operational received-by-cutoff snapshots require additional infrastructure and client acceptance.

## Latest eligible forecast

`latest_source_key_v1` applies independently to every expected target:

1. Restrict the target's source versions to publications at or before that decision's cutoff.
2. Find the greatest eligible publication time.
3. Deduplicate identical source-version IDs at that key.
4. Validate the selected key. Conflicting variants, nulls, negative generation, or source quality flags make it invalid. Retain the selected publication, version IDs, and reason, with a null usable value.

An invalid latest key does not fall back to an older valid forecast. A target with no eligible publication is `missing`, with `NO_PRE_CUTOFF_PUBLICATION`. Later publication identities, values, and times do not appear in the decision result. Targets can legitimately use different issue times. Age is cutoff minus selected publication time in seconds, including zero for an exactly-at-cutoff issue.

The Decision engine takes only a forecast index. Its output contains the delivery window, selected source facts, coverage, and mean/minimum/maximum of valid reported target values. It contains no actual observations, errors, or retrospective metrics. Publication-time bounds include selected invalid keys as well as valid keys so quality problems do not conceal an issue's age.

## Actual vintage and comparison

Accuracy is explicitly retrospective. Under `latest_publication_in_release_v1`, select the greatest actual publication for each target within the pinned accepted release, then validate that latest key. A newer null or conflict cannot be hidden by an older actual value. This evaluates the frozen reported outturn, which may include estimates; it is not certified final settlement truth. Actuals published after the original forecast cutoff are appropriate in this retrospective view and cannot enter the forecast-only Decision engine.

`source_timestamp_v1` compares a selected WINDFOR value with a valid FUELHH WIND value at exactly the same source `startTime`. WINDFOR source targets are hourly and FUELHH values are half-hour averages. This implements the brief's common timestamp without asserting that the sources have proven identical averaging semantics.

There are 744 expected forecast/comparison targets across the full range and 1,488 separate expected actual half-hours. All half-hour observations are retained for the later chart/table. Only actual points with a valid paired forecast at the identical timestamp have `used_in_metrics=true`. No forward filling, half-hour forecast interpolation, or hidden replacement of a missing value with zero occurs.

The optional full-hour mean interpretation is deferred. It would need both actual components, a distinct comparison policy, separate metrics, and a stated forecast-interval assumption. Source-time differences alone do not justify forecast MWh, energy error, procurement volume, or financial savings.

## Errors and metrics

For paired valid targets, error in MW is forecast minus actual. Positive means overforecast; negative means underforecast. Legitimate zero generation is valid. Preserve calculation precision and round only for presentation.

`metrics_v1` defines:

| Metric | Calculation |
| --- | --- |
| MAE | Mean absolute error |
| RMSE | Square root of the mean squared error |
| Signed bias | Mean signed error |
| P90 absolute error | Sort absolute errors and linearly interpolate at zero-based index `(n - 1) × 0.9` |

The implementation uses accurate floating-point summation and an integer decile rank for percentile interpolation. Range-level metrics pool all valid target errors, so a day with fewer pairs does not receive the same weight as a complete day. No-pair results return null for all four metrics and `NO_VALID_PAIRS`; a valid zero-error result returns zero. The sample count is a target count, not a claim that hourly errors are statistically independent. Historical P90 is descriptive and is not a calibrated future confidence interval.

## Coverage and missing reasons

Every expected hourly target has exactly one state, in this precedence:

| State | Meaning |
| --- | --- |
| `forecast_missing` | No forecast publication available by the cutoff |
| `forecast_invalid` | Latest eligible forecast key fails quality validation |
| `actual_missing` | Valid forecast but no actual source publication at the target |
| `actual_invalid` | Valid forecast but latest release actual key fails validation |
| `paired` | Both values valid; error and metric contribution exist |

The five counts sum to expected targets. Both selections retain their own evidence even when the primary reason follows this precedence. Paired coverage is paired divided by expected, not paired divided by whichever records survived a join.

Actual source coverage separately counts valid, missing, and invalid half-hours, using its own denominator. Reasons include `NO_ACTUAL_PUBLICATION`, `CONFLICTING_SOURCE_KEY`, `NULL_GENERATION`, `NEGATIVE_WIND_GENERATION`, and parser quality flags. A complete release at the two ingestion-validation cutoffs does not establish all future source availability; analysis calculates coverage for its actual filters.

## Reproduction and verification

The operator CLI pins the active release once, or accepts a full explicit accepted release ID. All subsequent source reads use that release's frozen parsed membership. Another release becoming active cannot change these results. Domain modules do not query the database or source APIs.

```text
uv run winddesk analyze --cutoff 09:00 --output output/analysis-0900.json
uv run winddesk analyze --decision-from 2026-01-31 --decision-to 2026-01-31 --cutoff 09:45 --output output/january-31.json
```

Operator JSON reports carry the release, parser, application build identifier, attribution, policy versions, daily points, selected version IDs/publications, original half-hour observations, metrics, and coverage. The Phase 4 public APIs additionally provide canonical context IDs and guarded CSV download links; see the [API contract](API.md).

Tests cover independent arithmetic, all five coverage states, unequal daily sample sizes, cutoff equality and exclusion, mixed issue times, revised actuals, null/conflicting latest keys, calendar boundaries, both clock changes, and deterministic results under input reordering. A separate frozen-source test calculates errors and summary metrics directly from raw JSON at 00:00, 09:00, 09:45, and 23:59 and compares them with the domain output. PostgreSQL integration checks the accepted-release adapter and original member identities while a reparsed release is active. See [Phase 3 evidence](PHASE_3_STATUS.md).
