# Phase 7 public deployment and verification

Verified on 30 October 2026. **Complete for the public evaluation pilot.** Open [Wind Desk](https://tme7d41m5t.vercel.app) without an account. The application retains the real January Elexon dataset in managed PostgreSQL. GitHub publication, remote CI, the required video and submission remain Phase 8 work.

## Deployed release

| Item | Verified value |
| --- | --- |
| Public URL | `https://tme7d41m5t.vercel.app` |
| Project / hosting plan | `tme7d41m5t` / Vercel Hobby |
| Runtime source commit | `77f0793b4d7bdc4cf95e3c8363d1d13f82567363` |
| Runtime | FastAPI/Python 3.12; React assets built with Node 24 |
| Configured function region | London, `lhr1` |
| Database | Isolated `tme7d41m5t-db`, Neon Free, London |
| Accepted release | `f61cecb1c14d91cfc32f10c74a9945fd2cf7f1851abd8ca6b0eb3f3e8975b052` |
| Schema / parser | `0002_freeze_release_versions` / `elexon_streams_v2` |
| Data | 19,856 forecast versions; 1,488 WIND actuals; 744 valid native comparison targets |
| Persistence check | Same source redeployed; accepted release and public result/export fingerprint unchanged |

The [machine evidence](phase-7-evidence.json) records the platform deployment IDs and check results. Vercel builds the function from source; it does not deploy our Docker image. Docker remains the separately verified local runtime. Later documentation commits can therefore differ from the runtime source above without changing the deployed application.

## Executed checks

- **Backend:** 107 tests passed, zero failures/skips, against local PostgreSQL with isolated test schemas. Tests were not run against the hosted production database.
- **Frontend:** the latest enhanced source passed 47 tests, lint, type checking and build; Phase 7 changed no frontend application code. The actual Vercel build also completed successfully.
- **Public API and CSV:** `scripts/verify_service.py` passed against the canonical public URL, before and after replacement deployment, without login or a protection-bypass token. Checks include cutoff eligibility, January/February boundaries, forecast-only Decision data, guarded downloads, all 1,488 retrospective CSV rows, four independently recomputed metrics, provenance, errors and built assets.
- **Fresh logged-out Chrome:** Decision, Accuracy and Methodology, cutoff application, daily drill-down, reload/share state, exact browser downloads, keyboard inspection, reference dialogs, reduced motion and 1440/390/320-pixel layouts passed. No console errors were recorded.
- **Hosted security:** HTTPS/HSTS, CSP and other application headers, cross-site API rejection, restrictive CORS, hidden API docs/OpenAPI, denied source maps, immutable assets and absence of database passwords in HTML/JS/CSS passed. An untrusted Host was rejected by the platform with 404.
- **Dependency audit:** the locked Python production environment for Linux/Python 3.12 reported 41 audited packages, zero known vulnerabilities and zero adverse statuses. The earlier unchanged frontend lockfile audit also reported zero vulnerabilities. These are dated advisory checks.

At 09:00 the public month result is MAE **2,022.470430107527 MW**, RMSE **2,497.407157584179 MW**, bias **+1,745.9381720430108 MW**, P90 absolute error **4,154.4 MW**. At 09:45, MAE is **1,995.5685483870968 MW**, with 744 pairs. Positive error means forecast minus actual; matching remains `source_timestamp_v1`.

The stable public fingerprint before and after replacement was `5ba13edaa4203eabb00cb6cb6e820420baf95f701eb0879c6fceecb22d3cebc9`. This demonstrates persistence across application replacement. It is not a managed-database restart, backup-restore drill or availability guarantee.

## Secrets, database and edge controls

The operator applied migrations and imported the checksum-validated bundled archive outside the web runtime. Only the separate `winddesk_reader` connection is stored in the Vercel project's sensitive environment setting. Its grants permit required release/fact reads and limited provenance columns; writes, schema changes, raw response payloads and ingestion records are unavailable. The role has a 20-connection cap, and each function pool allows one connection with no overflow. Verified TLS and the application read-only/timeouts remain enabled. The direct Neon endpoint was verified with these session options; the pooler is not assumed compatible without testing.

The initial hosted build reached deployment readiness but its data readiness failed. Portable CA resolution was added: `sslrootcert=system` resolves to the shipped `certifi` roots while retaining `sslmode=verify-full`. Explicit private CA paths are preserved. Safe categorized database diagnostics omit exception text, SQL and credentials. The corrected deployment and its replacement passed public readiness and analysis checks.

The temporary database integration connection was removed before runtime secrets were configured. Operator credentials are absent from the Vercel project's environment. An exact scan found none of the newly provisioned credentials in publishable files; six temporary provisioning secret files were then removed. The authorized official CLI login remains in private ignored local configuration, excluded from Git and application bundles. No `VITE_` secret exists.

Vercel's CLI reports **Mitigations Active**, **Firewall Enabled**, **2 active rules**, and no unpublished changes after publication. These free, project-specific deny rules are active:

| Rule | Conditions | Result verified remotely |
| --- | --- | --- |
| Read-only public portal | Method is POST, PUT, PATCH, DELETE, TRACE or CONNECT | POST/PUT/PATCH/DELETE to the API returned edge 403; GET pages/assets remained accessible |
| Block private-file probes | Path begins `/.env`, `/.git`, `/.cache` or `/.tools` | Four representative paths returned edge 403 |

Automatic DDoS mitigation remains active. Attack Mode, managed Bot Protection and OWASP rulesets remain off; no bypass rule was created. Priced WAF rate limiting/OWASP features were not enabled. [Vercel pricing](https://vercel.com/docs/vercel-firewall/vercel-waf/usage-and-pricing) distinguishes free custom rules from priced features. The existing protection on generated deployment URLs was retained; reviewers should use the public canonical URL above.

The application does not derive rate-limit identity from arbitrary forwarded headers. Its quota and cache are per process, so they do not establish a shared internet-wide quota. The role connection cap bounds reader sessions but can produce controlled unavailability during overload; it does not prove a particular simultaneous-user capacity. See [security and scaling](SECURITY_AND_SCALING.md).

## Reproduction, recovery and ownership

From a local environment with the locked dependencies installed:

```powershell
python scripts/verify_service.py --base-url https://tme7d41m5t.vercel.app --output output/phase7/service-recheck.json
$env:GRID_BROWSER_BASE_URL = 'https://tme7d41m5t.vercel.app'
$env:GRID_BROWSER_CHANNEL = 'chrome'
$env:GRID_BROWSER_OUTPUT = Join-Path $PWD.Path 'output/phase7/browser-recheck'
npm run test:browser --prefix frontend
```

The raw reports/screenshots live under ignored `output/phase7/`. Public API/browser checks require network access and installed Chrome; they do not require Vercel credentials. Avoid repeated bursts against the small free pilot. The loopback-only load tool is intentionally not used to load-test the public URL. `verify_security.py` is a local application gate: hosted ingress can return its own 403/404 instead of the application's JSON errors, so the separate recorded hosted checks account for those responses.

The normal local Docker application was also rebuilt from the same runtime source and locked dependency set, using the standard startup helper and preserving its database volume. Its accepted release and readiness passed after replacement.

For recovery, redeploy the last verified successful deployment recorded in the machine evidence with the existing reader environment, then rerun public service checks before accepting it. Do not select the initial failed-data-readiness deployment. Alternatively deploy the verified source commit with the same locked inputs and reviewed configuration. Web startup does not migrate or replace data. Retain the accepted release during rollback; a later schema-changing release needs its own compatibility plan. [Vercel setup](VERCEL_SETUP.md) supplies the operator procedure.

If the evaluation database is lost, an authorized operator can recreate an isolated database, apply migrations, re-import the bundled archive and re-provision the restricted reader, then update the sensitive runtime secret and redeploy. That seed-recovery path is documented; no timed hosted recovery or managed backup SLA has been demonstrated. The earlier separate-database local restore remains documented in [local readiness](LOCAL_READINESS.md).

The account owner retains hosting, usage review, incident response, secret rotation and eventual archive/removal responsibility. Vercel Hobby and Neon Free were selected, and no paid upgrade was purchased. Free quotas, cold starts and possible quota-based pauses apply. No automatic spending escalation or operational SLA is promised. The [Hobby plan](https://vercel.com/docs/plans/hobby) is for personal, non-commercial projects: this deployment is an individual assignment demonstration; client commercial use requires a separate hosting/plan review.

Before operational reliance, complete Phases 9–11: agreed trading semantics, scheduled/frozen operational data, distributed abuse/capacity controls, owned monitoring and alerts, managed recovery evidence, security review and client acceptance. Phase 8 still requires an actual public repository/remote CI run, unlisted video and final submission. Cumulative assignment effort has not been reconciled against the original sixteen-hour limit.
