# Local handoff and remaining release work

Prepared 30 October 2026, Asia/Calcutta. This supplements the historical phase records; it does not rewrite their original verification results.

**Later release update:** [Phase 7](PHASE_7_STATUS.md) has now deployed and verified the [public evaluation app](https://tme7d41m5t.vercel.app). Hosting items listed as pending in this earlier local handoff are superseded by that record; GitHub/remote CI and the video/submission remain Phase 8 work.

**Status: local technical handoff verified.** Docker Desktop 4.97.0 / Linux Engine 29.9.2 now runs the application at [127.0.0.1:8000](http://127.0.0.1:8000/). All 90 backend and 43 frontend tests passed from the repaired committed checkout. The complete container verifier, local helper, separate-database restore and normal Desktop restart checks passed. [Machine evidence](local-readiness-evidence.json) records the exact source and image identifiers.

## Start the complete local application

Start Docker Desktop with the Linux engine, then run from the checkout:

```powershell
.\scripts\local.ps1 -Action Start
```

The command builds the combined image, waits for PostgreSQL and the one-off migration/seed service, checks dataset readiness and prints the workbench URL. Defaults are [port 8000](http://127.0.0.1:8000/) for the app and 5432 for local PostgreSQL. Existing native processes on those ports must be stopped first; the helper does not kill other applications.

To run alongside an existing native preview:

```powershell
.\scripts\local.ps1 -Action Start -HttpPort 18000 -DatabasePort 15432
.\scripts\local.ps1 -Action Status -HttpPort 18000 -DatabasePort 15432
.\scripts\local.ps1 -Action Stop -HttpPort 18000 -DatabasePort 15432
```

Use the same ports and project name for subsequent operations. `-Project winddesk-local-review` selects an independent local Compose project when reviewing another checkout. The helper refuses to control a project owned by a different directory. `Stop` retains the database volume. PostgreSQL and web use `unless-stopped` restart policies; initialization remains a one-off operator step. The helper restores its temporary environment overrides before returning.

On other operating systems, use the README's Docker Compose commands. Python and Node installations are needed for development or the verification runners, but the application-only startup builds them inside Docker.

## Verification sequence

1. Run the publication-input check before committing. Keep `.env`, local caches, assignment material and generated output out of Git.
2. Create a local source commit using the configured Git identity; do not publish it during local-only work.
3. Clone that local commit into an empty directory and install only the locked dependencies needed by the verification commands.
4. Run the isolated container verifier from the clone, pinning `GRID_BUILD_SHA` to the source commit. This checks clean build, real seed, browser journey, CSV arithmetic, seed replay and database/application restart.
5. Verify the standard local Start/Status/Stop path, Docker Desktop restart behavior and preservation of existing unrelated Docker workloads.
6. Record the source commit, image ID, actual results and any limits in `local-readiness-evidence.json`.

The earlier 90 backend and 43 frontend tests remain recorded in [Phase 6](PHASE_6_STATUS.md). Repeat checks when a changed implementation or a new platform concern warrants them. The [verification guide](VERIFICATION.md) contains the individual commands. A local run does not replace a remote GitHub Actions result.

The tested source commit is `c1afaa1490e179c36bd9ee0cb878a4ca587df7f6`, following the local root commit `06db509`. The final handoff adds documentation/evidence without changing application behavior. No commit was pushed or published. The first cold test run exposed a missing parent for `.cache/pytest`; pytest now uses the directly creatable, ignored `.pytest-tmp` directory, which is also excluded from Docker/Vercel and publication inputs.

The clean environment used installed CPython 3.12.14 explicitly after uv encountered a broken machine-wide managed-Python minor-version link. A developer encountering that local tooling problem can run `uv sync --frozen --python C:\path\to\Python312\python.exe`. This does not change the dependency lock or the application-only Docker path.

A separate local staging check copied the tracked files through the Vercel upload exclusions, installed the locked frontend dependencies and passed TypeScript plus the production build. The upload keeps fixtures needed by the full TypeScript check; function-bundle exclusions omit frontend source/tests and operator helpers after build. This fixes an omission that would otherwise leave the checked test modules importing missing fixtures. The staged input contained no `.env` or backend test tree. This is a local packaging check, not an authenticated Vercel build or hosted verification.

## Docker Desktop repair

The reported failure occurred before the application could run: Docker Desktop 4.91 could not rename an inaccessible `sailor-ingest.sock` runtime entry. Preserving the socket-only parent folders restored one startup, but a normal restart reproduced the error. The installed version was therefore updated in place using Docker's official 4.97 installer, verified against its published SHA-256 and a valid Docker Inc code signature.

Before installation, both Docker data disks were backed up privately with matching checksums. The installer preserved both original disk files byte-for-byte. Runtime-folder backups were retained, and no factory reset, WSL unregister, image prune or deletion of existing workload volumes was used. Restart and application verification results belong in the final evidence record rather than being assumed from installation success.

The updated Desktop completed a normal stop/start without another runtime-folder repair. PostgreSQL and web returned automatically, and the complete dataset/JSON/CSV fingerprint was unchanged. Both original unrelated containers and volumes were preserved. The earlier native preview was replaced by the verified Docker application on the same port; the native database is retained and stopped.

A 2,878,592-byte custom-format `pg_dump` of this project's database was restored to a newly created separate database. A read-only application container using that restore reproduced the same release, metrics, JSON and CSV fingerprints. Only the temporary restore database and container were removed. This is local recovery evidence; hosted backups, restore timing and operational ownership still need their environment-specific acceptance.

Related first-hand reports are available in [Docker's Windows issue tracker](https://github.com/docker/for-win/issues/15064); the official [Windows installation guide](https://docs.docker.com/desktop/setup/install/windows-install/) describes the update/install controls. An update is verified by an answering Linux engine and completed restart/application checks, not merely its installer exit code.

## Submission preparation

The [customer and technical demo script](DEMO_SCRIPT.md) is ready for the final recording. Keep each initial overview under five minutes and the whole video under ten. The eventual README must contain real application and video links.

The following work depends on external accounts or final submission actions and remains separate from local technical readiness:

- Verify Vercel account/plan access, approved cost ownership and an external PostgreSQL database.
- Configure hosted secrets, trusted proxy identity and host-level quotas; deploy and check public HTTPS and persistence.
- Publish the anonymous-name GitHub repository and obtain an actual successful remote CI run from the committed source.
- Record/review the final demonstration, upload it unlisted, verify logged-out playback and fill in the actual links.
- Check the final submission artifacts and submit through the company's requested process.

Operational utility launch remains the separately scoped acceptance, identity/access, ingestion, recovery, monitoring and performance work in Phases 9–11. Local pilot completion does not imply that those client-dependent controls have been approved.
