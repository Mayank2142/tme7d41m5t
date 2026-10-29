# Pilot Data and Decision Contract

Status: adopted for the assignment pilot, 29 October 2026. Operational use still requires client/data-owner acceptance. See the implementation plan for supporting source research.

The purchase-decision calendar is 1–31 January 2026 in Europe/London. Delivery is the following UK civil day, so the combined source actuals window includes all of 1 February. The default desk cutoff is an illustrative 09:00 local time, not an asserted exchange gate closure.

Select the greatest eligible source publication time independently for each forecast target, inclusively at the cutoff. Validate that latest source key after selection. Nulls or conflicts cannot be concealed by filtering invalid rows first and taking an older value.

The default comparison policy is `source_timestamp_v1`: compare WINDFOR and FUELHH WIND values sharing the same target `startTime`. Source forecast targets are hourly; actual observations are half-hour averages. This compares reported source-time values, without manufacturing half-hour forecasts or claiming proven matching interval semantics.

An optional `hourly_mean_v1` analysis must be separately labeled, require both actual half-hours, and disclose its full-hour forecast interpretation. Forecast energy totals are not valid under a point-matching policy alone.

Historical availability uses Elexon source publication time. Download time does not prove January receipt by a trading desk. A future operational mode additionally needs actual application receipt before its cutoff. Retrospective actuals use a frozen source vintage; future actual values are excluded from the Decision DTO and UI.

Phase 1 exposes the pilot policies through `/api/v1/config`. Phase 2 implements ingestion and frozen release membership. Phase 3 implements shared source-key selection, source-time comparison, metrics, and explicit coverage; see [methodology](../METHODOLOGY.md). Public analysis contracts and CSV follow in Phase 4.
