# URL State, Read Contracts, and Accessible Source Charts

Adopted during Phase 5 on 29 October 2026.

Build three React views over the existing API rather than recalculate headline metrics in the browser. A typed client validates supported policies, selected dates/cutoff/release, expected target grids, selected publications, coverage reconciliation, source URLs, and export context before exposing results. The API remains authoritative for selection, vintage, and metrics.

Separate draft form state from applied URL state. Preserve the decision date, accuracy range, cutoff, and pinned release across all tabs and shared addresses. Send only relevant filters to each API. React Query keys include the effective mode and active filters; changed filters do not use another query's placeholder data. Abort signals, explicit refresh errors, and disabled unsettled downloads avoid stale selection/label combinations.

Use the returned guarded export URL. Verify CSV content type and context/release headers before creating a temporary browser blob URL, then release it. Configuration is refreshed explicitly when selecting the current source release; an existing explicit pin is preserved until that action. Calculation/build changes remain covered by the server's expected-context check.

Use native SVG for source-time generation and signed-error plots. Keep null gaps and legitimate zeros, use native timestamps for axis labels, and avoid a smoothing or energy interpretation. Provide a keyboard target slider with value text, an exact-value inspector, semantic tables, and restrained positive/negative styling. Preserve all original half-hour actual points in Accuracy while identifying the hourly comparison denominator separately.

Record runtime and interaction checks separately. Offline frontend tests use attributed real API fixtures; failure, partial, and empty variants are confined to tests. No production fixture fallback or source values are synthesized. A single documented lint exception allows keyboard focus on named scroll containers; the accessibility purpose is explicit in the component.

The browser journey verifies the real PostgreSQL-backed service, actual download files, native keyboard behavior, route/history transitions, and desktop/narrow layouts. Public deployment, CI, ingress controls, load measurements, and broader assistive-technology verification retain their later completion gates.
