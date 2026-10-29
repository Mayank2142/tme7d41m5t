# 0007 Reproducible verification and read-only runtime

Status: accepted for the assignment pilot, 29 October 2026.

The release gate uses the attributed frozen January source archive and real PostgreSQL. External source availability must not determine an ordinary CI result. Domain fixtures cover adversarial temporal and missing-data cases; integrated service checks independently recompute metrics from CSV; a browser library runner verifies the actual connected analyst journey and downloaded bytes.

The same non-root combined image serves the React build and Python APIs. Its base manifests and dependency locks are pinned. Compose serializes database readiness, one-off migration/seed and web startup. Application containers have a read-only root, scratch tmpfs, no added capabilities and no privilege escalation. Seeding writes to PostgreSQL; writing a filesystem report is an explicit operator option. The image build identifier is included in both its OCI label and public analysis context.

CI has separate quality and container jobs, minimal repository permissions and immutable Action references. Its disposable Compose project checks seed replay and database/application restart consistency, cleans up only its own resources and retains evidence on failure. No live Elexon call or deployment credential is needed.

A per-process direct-peer request quota and browser security headers provide pilot backstops. Shared quotas and verified proxy identities remain host-specific deployment work. Swagger has a separate CSP because the generated documentation loads its own assets and initialization script. Authentication, restricted production database roles, recovery exercises, measured performance and utility acceptance remain later operational work.

Verification records must distinguish a local source snapshot from a committed clean checkout, image execution from configuration validation, and a prepared workflow from a completed remote CI run. See [verification commands and limits](../VERIFICATION.md).
