# Offline frontend fixtures

The JSON fixtures were captured from the local Phase 4 read APIs backed by the accepted Elexon release `f61cecb1c14d91cfc32f10c74a9945fd2cf7f1851abd8ca6b0eb3f3e8975b052` on 29 October 2026. They retain the API's source attribution, source-version identities, timestamps, policy versions, context, and guarded export URLs.

- `configuration.json`: source readiness and pilot configuration.
- `decision.json`: 31 January decision at 09:00, covering 1 February delivery.
- `decision-later.json`: the same decision at 09:45.
- `decision-january-1.json`: 1 January at 09:00, including the documented 18,781 MW midnight forecast.
- `accuracy.json`: retrospective 1 January decision analysis at 09:00.
- `accuracy-month.json.gz`: complete January analysis at 09:00, compressed to avoid a large repeated text fixture.
- `quality.json`: the accepted release's validation and original-response provenance.

Tests mutate copies to model failures, different pins, partial coverage, and empty data. Those edge cases are synthetic test scenarios and never enter the production application. Product source files do not import this directory, and the Vite application build does not bundle these fixtures. Normal tests require no live Elexon or database service.

Contains BMRS data © Elexon Limited copyright and database right 2026. See the repository's `data/ATTRIBUTION.md` for the applicable licence.
