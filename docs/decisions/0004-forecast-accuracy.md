# Shared Temporal Selection and Pure Accuracy Calculations

Adopted during Phase 3 on 29 October 2026.

Move the normalized source fact type into the domain and use one latest-key selector for ingestion validation and analysis. The ingestion compatibility adapter preserves its recorded validation reasons, parser version, normalized fingerprints, and existing release identity. Source facts remain unchanged by this refactor.

The selector chooses the greatest eligible publication before checking its variants and quality. It returns only eligible selected identities and explicit missing/invalid states. Invalid usable generation is null; raw values remain in immutable source storage. Source indexes group by target and dataset and prevent the decision engine from accepting actual records.

Separate forecast-only `DecisionAnalysis` from retrospective `AccuracyAnalysis`. Domain functions consume in-memory source facts and never query storage, use wall-clock time, or call external APIs. Construct civil-day boundaries locally and traverse the UTC target grid. Limit decisions to the adopted January contract while testing the reusable day-boundary function at both UK clock changes.

Implement only `source_timestamp_v1` in this phase. Preserve the unscored half-hour actual observations and report their source coverage separately. Classify every expected forecast target using the precedence recorded in the plan. Pool range-level errors before computing `metrics_v1`, return null metrics for no pairs, and retain full calculation precision.

The PostgreSQL adapter resolves one accepted release and reads only its immutable parsed members. Explicit unknown/rejected release IDs fail. A new operator `analyze` command makes the result concrete and reviewable before exposing the Phase 4 API and Phase 5 interface. Public context hashing, CSV, and user-facing controls remain those phases' work.

The source-time versus full-hour averaging uncertainty remains a visible pilot limitation. No percentile is promoted to a procurement buffer or confidence interval, and no energy or money calculation is introduced.
