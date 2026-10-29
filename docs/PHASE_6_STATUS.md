# Phase 6 Integrated Verification, Docker and CI

Recorded 29 October 2026 UTC; precise work timing is in the machine evidence.

Follow-up on 30 October, Asia/Calcutta: [local readiness](LOCAL_READINESS.md) records the subsequent Docker Desktop repair, local startup handoff and actual committed-checkout verification. The original checks and environment observations below remain historical evidence.

**Status: implemented and verified locally, including real container execution.** CI is configured and statically validated. No GitHub repository, remote Actions run, public deployment or video has been created in this phase. This remains an assignment pilot; operational production acceptance is a later scope.

## Delivered

- Standalone service verification using the real frozen Elexon release, canonical contexts, source provenance, safe read-only routes and independent metric recomputation from both cutoffs' CSV.
- Repeatable real-browser journey, exact browser-download byte checks, keyboard controls, daily drill-down, pinned cross-view state/reload, console checks and responsive screenshots.
- A pinned multi-stage image, build identity in OCI/API contexts, non-root runtime and Compose restrictions for a read-only root, scratch tmpfs, dropped capabilities and no privilege escalation.
- An immutable-input seed command: migration/import no longer rewrites the adjacent manifest. Report writing requires `--report`.
- API request backstop, `Retry-After`, safe quota errors, request references, browser security headers, a scoped Swagger policy, production HTTPS HSTS and cache rules.
- Publication-input/credential checks, packaged-wheel migration validation and an isolated Compose verifier that refuses existing project resources and cleans up its own project.
- A two-job CI workflow with real PostgreSQL, frozen data, lint/types/tests/build, image/startup/browser/replay/restart checks, minimal permissions, pinned Actions and bounded evidence retention.

See [verification commands and limits](VERIFICATION.md) and the [architecture decision](decisions/0007-release-verification.md).

## Checks actually executed

| Check | Result |
| --- | --- |
| Python suite, including real PostgreSQL | **90 passed, 0 skipped**, 209.86 seconds; five database integration tests |
| Frontend suite | **43 passed**, five files, 54.66 seconds in the concurrent run |
| Python lint and formatting | Passed, including the verification scripts |
| Frontend lint, TypeScript and production build | Passed |
| Frozen Python lock check | Passed offline; 41 resolved packages |
| Wheel build and packaged migration/CLI check | Passed with pinned Hatchling 1.33.0 |
| npm dependency audit | 0 reported vulnerabilities in the explicit final audit; metadata counts 166 dependencies |
| Publication-input scan | Passed; final count recorded in machine evidence |
| CI validation | actionlint 1.7.12 passed; official release ZIP checksum verified |
| Compose configuration | Passed |
| Native PostgreSQL-backed service/CSV gate | Passed; all four metrics independently recomputed at 09:00 and 09:45 |
| Actual Chrome journey and CSV downloads | Passed, 0 console errors, 1440/390/320-pixel viewports |
| Container build and clean initialization | Passed from the clean source snapshot, without local environments or dependencies |
| Container service/CSV and Chrome journey | Passed against the actual image on port 18000 |
| Container restrictions and existing-project guard | Non-root, read-only root, tmpfs, ALL capabilities dropped, no-new-privileges; running project and orphaned volume both refused and preserved |
| Seed replay and PostgreSQL/web restart | Passed; release, JSON and CSV fingerprints identical before and after |
| Complete reusable container CLI | Exited 0 for a second fresh project, including automatic cleanup |
| Remote GitHub Actions | Not run; repository publication is later work |

The service gate checked the January 1 example (18,781 MW), January 31 → February 1 boundary (10,099 MW at 09:00; 10,474 MW at 09:45), 744 paired targets and 1,488 preserved half-hour CSV rows per cutoff, ten raw-response digests, stale-context rejection and the absence of retrospective fields from Decision. Coverage and metric arithmetic continue to use the Phase 3 policies.

The native browser downloaded a 16,684-byte Decision CSV and 1,220,393-byte full-month Accuracy CSV at 09:45. With the container's `phase6-local` build marker, the corresponding files contain 16,852 and 1,230,809 bytes; contexts and CSV include the longer build identifier by design. Exact hashes are in [machine evidence](phase-6-evidence.json). Screenshots were rendered and inspected; artifacts and JUnit reports are ignored local output, while this compact evidence record is publishable.

The clean-source image ID was `sha256:8e88e751bc38cc5fb43c0037b8b47e72f1ac23fe802d0af6718165a81e625e7b` (283,881,202 bytes), with build marker `phase6-local`. Its initializer migrated an empty PostgreSQL volume and accepted the real release on the first start. A second initializer exited successfully on the read-only root. After restarting PostgreSQL and web, the full service gate produced the same stable fingerprint: `54c9e04926ac299c8b104d2022fbbcac136a9c7e86fda93a4f3cdb9a4c71fe3b`.

The complete `verify_containers.py` command was then exercised from the current workspace as a second disposable project. It exited **0**, with image `sha256:90a959cf922642d1437c50022c71de8a5a2807655d7a27ebd2f1b3e884eb4429` and before/after fingerprint `f2ea37e3d747d480916aafb1f7a610aaec81d7da0ec7a9c414b008f9189df86d`. A temporary npm adapter invoked the same Windows Chrome runner from Linux; it is not part of the repository or deployment. CI is configured for native Linux Playwright Chromium, which still needs its actual remote run. Separate fresh databases have separate release-publication timestamps, so their aggregate quality fingerprints need not match each other; each database's fingerprint remained unchanged across its own restart. Source selections, metrics and CSV identity match.

## Container environment and evidence boundaries

Docker Desktop initially had no Linux engine. A hidden startup attempt failed on its existing `sailor-ingest.sock` reparse-point entry. Narrow rename/removal/metadata repair attempts returned Windows error 1920; Docker data and volumes were not reset. The failing test-started Desktop processes were stopped.

An existing Ubuntu 24.04 WSL2 environment provides the alternative test host. Official Docker Engine 29.8.0 binaries live under ignored workspace tooling, with a private Unix socket and newly created temporary data root. Ubuntu's missing iptables package and dependencies were installed for normal Docker networking. No Windows service, cloud resource, global Docker context change or unprotected TCP Docker API was created. This static test engine is not a proposed production installation; [Docker's documentation](https://docs.docker.com/engine/install/binaries/) distinguishes binary testing from a maintained production installation.

Both disposable projects and their volumes were removed after verification. The private engine was stopped, and the native preview/database on ports 8000/5432 remain available. Docker Desktop still needs its separate environment repair.

The source snapshot was copied from Git's tracked/non-ignored input list into an empty ignored directory, without `.env`, environments, dependencies, caches, local output or the supplied assignment document. Its application source and locked inputs match the current application. The repository has no initial commit yet, so this is explicitly a **clean source copy**, not a claimed fresh Git clone. The eventual committed checkout and remote CI run remain publication gates.

## Corrections and remaining boundaries

The read-only seed/report regression was fixed before container verification. Initial local wheel packaging failed because its isolated build backend needed registry access; rerunning with network access and an exact verified build-backend version succeeded. The first CI-validator download selected a `.tar.gz` name while Windows publishes a ZIP; the correct checksum-verified asset was then used. A script lint line was corrected and checks passed.

Visual review exposed an off-screen fixed skip link appearing inside a full-page screenshot after browser auto-scrolling. Capturing from the top fixes that screenshot artifact; the application source did not change. The browser gate also verifies actual horizontal table scrolling by keyboard. These targeted runner changes justify the final browser rerun.

The configured request quota is per direct peer and process, not a shared serverless limit. Configure host-level quota/proxy identity in Phase 7. Full authentication, restricted production database roles, recovery exercises, accessibility auditing, vulnerability maintenance and measured performance/availability remain later operational work. No production-readiness guarantee is inferred from a local pilot test pass.

Phase 7 covers the selected Vercel account, external PostgreSQL, hosting permissions/cost ownership, HTTPS, public browser checks and hosted persistence. Actual repo/application/video links must be added only after those artifacts exist.
