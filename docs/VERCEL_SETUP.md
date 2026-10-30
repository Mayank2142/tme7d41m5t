# Vercel deployment and operator guide

The [public evaluation app](https://tme7d41m5t.vercel.app) is deployed and verified. [Phase 7 status](PHASE_7_STATUS.md) and [machine evidence](phase-7-evidence.json) record the actual source, resources and check results. This guide supersedes the earlier preparation-only instructions.

## Architecture and selected plans

Vercel imports `app` from the root `app.py` using its FastAPI framework support. The locked React build produces `frontend/dist`, included in the function bundle and served by the same FastAPI factory as the API. Python is constrained to 3.12, Node is 24, and `vercel.json` configures `lhr1` and a 30-second function maximum. Function exclusions and `.vercelignore` omit secrets, local dependencies, tools, caches, assignment material and generated test output. Frontend tests/fixtures remain in build input for type checking; runtime bundling excludes their source.

Project `tme7d41m5t` uses Vercel Hobby. Its separate `tme7d41m5t-db` database uses Neon Free in London. No paid upgrade was enabled. The existing unrelated storage resources were not changed. The personal assignment demonstration must stay within the selected plans' terms and allowances; commercial operation needs a separate plan review. Docker is the reproducible local runtime, not Vercel's deployment format.

Official references: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [Hobby plan](https://vercel.com/docs/plans/hobby).

## Runtime settings and secrets

Configure these in Vercel's environment settings for the intended deployment target:

| Setting | Value / purpose |
| --- | --- |
| `GRID_DATABASE_URL` | Sensitive **reader** connection URL; never the migration/operator login |
| `GRID_ALLOWED_HOSTS` | `["tme7d41m5t.vercel.app"]` |
| `GRID_BUILD_SHA` | Exact deployed runtime source commit from the evidence record |
| `GRID_ENABLE_API_DOCS` | `false` |

The checked-in `vercel.json` supplies production mode, `frontend/dist`, pool size one and zero overflow. The platform supplies `VERCEL=1`. Only in that environment, configuration extends the explicit host allowlist with valid exact `VERCEL_URL`, `VERCEL_BRANCH_URL` and `VERCEL_PROJECT_PRODUCTION_URL` names. Wildcards and untrusted request forwarding headers are not used. Existing generated-deployment URL protection remains enabled; share the canonical public alias with reviewers.

The database secret follows this **placeholder-only** form:

```text
postgresql+psycopg://READER:replace-with-random-password@HOST/DATABASE?sslmode=verify-full&sslrootcert=system
```

Use a random password of at least 16 characters and encode reserved URL characters. The engine maps `sslrootcert=system` to the packaged `certifi` CA roots, avoiding base-image trust-store path differences while preserving hostname/certificate verification. An explicit private CA path is preserved. The verified deployment uses Neon's direct endpoint; do not switch to a pooler until its startup/session options pass readiness and analysis checks.

The web reader has SELECT on the required seven release/fact tables and only five provenance columns from raw batches. It cannot select raw payload bytes or ingestion runs, write data, create schema objects or manage roles. Its connection cap is 20. Web connections also set read-only transactions, bounded connection/statement/lock/idle-transaction timeouts. A pool of one per function does not itself bound the number of function instances; the role cap is a final database backstop.

Migrate/seed through a separate controlled operator session. `winddesk seed --configure-reader` reads `GRID_READER_DATABASE_URL` to provision the restricted login where the operator may manage roles. Apply migrations and validate the bundled accepted release before updating runtime configuration. Do not store operator credentials in the web project, expose secrets with `VITE_` prefixes or commit local auth/env files. The temporary Marketplace project connection was removed; runtime uses only the manually configured reader secret.

## Deployment and verification

Use the repository root and the checked-in build settings. The official Vercel CLI is authorized for this account; keep its local credential directory private. Link the intended project explicitly before deploying. Set `GRID_BUILD_SHA` to the reviewed code revision, then run:

```text
vercel deploy --prod
python scripts/verify_service.py --base-url https://tme7d41m5t.vercel.app --output output/hosted-service.json
```

The CLI may require the account's selected scope/auth directory. Verify readiness, accepted release, built assets, cutoff eligibility, metrics, exports and security through the canonical URL. Run the existing Chrome smoke with `GRID_BROWSER_BASE_URL` set to the same URL in a fresh browser context. A successful platform build alone does not prove database readiness.

For a replacement/persistence check, select a **successful** deployment ID from `phase-7-evidence.json`:

```text
vercel redeploy DEPLOYMENT_ID --environment production
```

Repeat the service checks and compare the accepted release, build and stable fingerprints. Phase 7 performed this successfully. Recovery to that verified source/settings uses the same procedure; verify before accepting the result. The initial failed-data-readiness build is not a recovery candidate. Keep the accepted dataset and compatible schema unchanged during an application rollback.

## Active edge controls and operational limits

The project has automatic DDoS mitigation and two published free custom deny rules: unsupported write/unsafe methods, and private-file path prefixes. The precise conditions and remote 403 evidence are recorded in Phase 7. They apply only to this project. Inspect with `vercel firewall status` and `vercel firewall rules list`; review `vercel firewall diff` before publishing a later rule change. Normal analyst GET pages/assets and downloads passed after activation.

No priced rate-limit or OWASP feature was enabled, and managed Bot Protection/Attack Mode are off. [Current WAF pricing](https://vercel.com/docs/vercel-firewall/vercel-waf/usage-and-pricing) distinguishes these from free custom rules. Process-local quotas and caches remain bounded but are not shared across instances. Do not enable forwarding-header trust until end-user identity has been verified through the actual ingress. Representative sustained cloud traffic, shared limits, usage/cost alerts, p95/p99 latency, 429/503 rates and connection exhaustion require an owned operational review; local burst results are not a cloud SLA.

The account owner manages usage review, incidents, secret rotation, evaluation retention and eventual removal. No evaluation removal date or automatic paid upgrade has been set. The bundled immutable archive supports an operator-led reconstruction into a new database if necessary, but hosted backup/restore timings and recovery objectives have not been demonstrated. See [security and scaling](SECURITY_AND_SCALING.md) and Phases 9–11 before client operational reliance. GitHub/remote CI and the mandatory video/submission remain Phase 8.
