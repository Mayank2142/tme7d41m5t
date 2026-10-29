# Release-Pinned Read Contracts and CSV

Adopted during Phase 4 on 29 October 2026.

Use typed query models and separate Decision/Accuracy response models. Reject unknown, repeated, and mode-incompatible filters. Keep route handlers thin: each calls the same application service used by CSV. Domain selection and metrics remain in the Phase 3 modules.

Resolve one accepted release before reading any source facts. The read adapter accepts that explicit immutable identity for all later queries. Decision loads only WINDFOR. Accuracy loads both sources from the same release. Quality queries also accept an explicit accepted release. Preserve the established API provenance field `payload_sha256`; the raw archive manifest's `sha256` field is a separate format.

Hash a versioned, canonical context containing the effective filters, mode, release, parser, relevant calculation policies/resolutions, and application version/build. Return a pinned export URL with an expected context check. A mismatch returns 409. Include the same release/context in response headers and every CSV row. Do not store request-specific context state or re-read the active pointer during the calculation.

Accuracy CSV uses one row per expected half-hour, with separate `comparison_target` and `actual_only` row types. This exports the full filtered series while preserving exactly 744 expected native comparison targets across January. Only valid paired rows contribute errors and metrics. Decision CSV has forecast columns only. Empty numeric cells mean null/inapplicable; numeric zero and negative errors remain numeric. Escape CSV syntax and neutralize formula-prefixed text.

Bound work to the assignment's thirty-one decision days. Build each export before returning a successful response. Use safe JSON errors with stable codes and request IDs, retain liveness/readiness separation, and emit request metadata without source payloads or credentials. No normal read calls the upstream API or publishes a release.

There is no analysis cache in this phase. Immutable release membership makes separate source reads consistent. Later performance work can introduce caching only with the complete context as its key. The development build marker `local` is explicitly distinguished from a verified deployed commit. Frontend controls, ingress limits, load targets, Docker execution, and public deployment retain their separate completion gates.
