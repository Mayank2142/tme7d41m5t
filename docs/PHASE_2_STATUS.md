# Phase 2 Data Pipeline Verification

Recorded on 29 October 2026, Asia/Calcutta.

**Status: implemented and verified locally against PostgreSQL 17.11.** The accepted real January dataset is persisted, reproducible, and visible through application metadata. Operational hosting is still local; no Vercel deployment or paid database was created.

## Delivered

- Bounded Elexon client with explicit deadlines, retries, response-size limits, and resumable request-window checkpoints.
- Original-response archive with byte-level SHA-256 integrity checks, source queries, receipt times, and verified attribution.
- Strict normalization, null/negative/metadata quality reasons, source-key conflict preservation, and January coverage validation at 09:00 and 09:45 GMT.
- Two explicit Alembic migrations for source evidence, versioned records, immutable releases, and frozen parsed-version membership.
- PostgreSQL persistence with duplicate-safe inserts, transactional activation, rejected-candidate isolation, and immutable evidence triggers.
- Operator commands for migration, fetch, seed, validation, refresh/backfill, and archive recovery.
- Bundled real-data seed and manifest; Compose initialization service; runtime image configuration includes the seed.
- Updated readiness, configuration, source-quality endpoint, and UI showing the real accepted release without pretending the analysis engine is complete.

## Current accepted data

| Measure | Result |
| --- | ---: |
| Source request windows | 10 |
| WINDFOR versions in this release | 19,856 |
| FUELHH WIND versions in this release | 1,488 |
| Valid actual half-hours | 1,488 of 1,488 |
| Forecast targets available by 09:00 GMT | 744 of 744 |
| Forecast targets available by 09:45 GMT | 744 of 744 |
| Source-key conflicts / invalid source versions | 0 / 0 |
| Decision dates | 1–31 January 2026 |
| Delivery dates | 2 January–1 February 2026 |

The full release ID, per-day report, parser version, normalized-content fingerprint, source URLs, payload hashes, and receipt timestamps are recorded in `data/snapshots/manifest.json`. The active release ID begins `f61cecb1c14d`. Archive counts include all relevant publication response vintages; they are not forecast-error sample counts or a claim of statistical independence.

## Checks actually run

The full backend run passed **22 tests**, including the real PostgreSQL integration tests with no integration skips. The frontend passed **8 tests**, lint, type checking, and the production build. Python lint/format and the dependency lock check passed. Compose configuration parsed successfully; a Docker image/Compose execution is not claimed.

PostgreSQL checks verified:

- Applying both migrations matches the ORM metadata.
- Repeated imports preserve the same release identity and do not duplicate source versions.
- Updating an immutable source record is rejected by PostgreSQL.
- A candidate missing one actual interval is rejected and cannot replace the active release.
- A later parser's versions for the same raw bytes cannot change an older release's members.
- Exporting original responses and re-importing reproduces the current release identity.
- A corrupt payload hash is rejected and recorded as a failed import.
- Readiness and metadata follow the accepted active release.

Live HTTP checks confirmed 200 responses from `/health/ready`, `/api/v1/config`, and `/api/v1/data-quality`, with the same release identity. The quality endpoint returned all ten source-request provenance entries without raw payloads or database credentials. The Windows portable PostgreSQL cluster was stopped and restarted; the accepted release identity persisted. A launcher exit-code issue found during this check was corrected before the successful restart verification.

Chrome verified that the page displays “January source data is ready,” the actual source record counts, the release identifier, source-quality link, and required attribution. Charts and accuracy metrics remain visibly not enabled because they belong to subsequent phases.

## Local database and remaining limits

Docker Desktop's Linux engine is still unavailable. The official portable PostgreSQL distribution was downloaded into ignored `.tools` storage, and its cluster is under ignored `.cache/postgres/data`. It listens only on `127.0.0.1:5432`; no Windows service, feature upgrade, reboot, or data reset was used. Its source URL and archive checksum are recorded in the local dependency provenance file `.tools/postgresql-source.json`.

The current helper `scripts/local-postgres.ps1` controls this already-prepared cluster. Stop it before Docker PostgreSQL is started on the same port. A clean reviewer setup uses the checked-in Compose definition or a configured PostgreSQL service, not this uncommitted binary cache.

Vercel account authentication, external database provisioning, budget/plan eligibility, public deployment, Docker runtime execution, scheduled ingestion, production access roles, backup policy, and operational service objectives remain unverified or later-phase work. The local development role is not presented as a production least-privilege configuration.

## Next phase

Phase 3 builds the reusable decision calendar, arbitrary cutoff selection, source-time pairing, error metrics, coverage ledger, and decision-versus-retrospective rules on the frozen release members. The current validation helper establishes source completeness; it does not implement the complete analyst accuracy experience.
