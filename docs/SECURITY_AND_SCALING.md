# Security and concurrency

The selected product is a **public, read-only** assignment demonstration using public Elexon national wind data. The user confirmed that company reviewers should not need accounts. Anyone can read the published forecasts, actuals and CSV exports. Protecting confidential client positions, consumption or purchases would require a separate identity/authorization design before adding those datasets.

## Implemented controls

| Area | Behavior |
| --- | --- |
| Repeated work | One application-scoped reader caches immutable source indexes. JSON and CSV are serialized once per normalized analysis key. Concurrent callers for the same cold key share one loader. |
| Correct cache identity | Keys include mode, dates, cutoff, accepted release, parser and build. Every analysis request still resolves the accepted release against PostgreSQL. Active-pointer changes and unavailable/revoked releases are observed before cached content is served. Export context checks still run on every download. |
| Bounded retention | Response cache: 128 entries, 32 MiB of accounted serialized payload by default. Source cache: four indexes, 32 MiB of conservative accounting. Both use a 10-minute TTL and LRU eviction. Oversized entries are served without retention; errors are not cached. These are accounting limits, not a hard process RSS limit. |
| Admission control | Up to 64 API/readiness requests may compute concurrently per process. Excess requests receive JSON 503 with `Retry-After: 1`. There is no additional application admission queue. The framework still has a bounded worker-thread pool. Liveness is asynchronous and independent of PostgreSQL. |
| Rate limits | Default: 120 requests per direct peer per sliding minute for `/api/v1/*` and `/health/ready`. JSON 429 includes `Retry-After`. Client tracking and retained timestamps are bounded; a new identity cannot evict another active quota. |
| Request limits | Reject URLs over 4,096 bytes, over 64 headers or 16 KiB of aggregate header names/values. Reject unsupported methods and bodies on this read-only service before database access. Cross-site browser API requests carrying Fetch Metadata are rejected. These checks supplement ingress limits; they do not stop a network flood before traffic reaches Python. |
| Host and proxy trust | Explicit hostname allowlist. Production requires `GRID_ALLOWED_HOSTS`; wildcard hosts are rejected. Uvicorn ignores forwarding headers by default. `GRID_TRUSTED_PROXY_IPS` accepts explicit IPs/CIDRs only and rejects universal networks. Only configure it when direct access is restricted to those trusted proxies. |
| Database privilege | Compose initialization uses the operator login; the web container gets a separate reader login. Only the seven required fact/release tables and five raw-batch provenance columns are granted SELECT. No access to raw payload bytes or ingestion runs, no write/DDL grants, no superuser/role-management privileges. Provisioning is idempotent and refuses a privileged/object-owning existing role. |
| Database limits | Web connections default to read-only transactions, a 5-second statement timeout, 1-second lock timeout and 5-second idle-in-transaction timeout. Connections have a 3-second connect timeout and a bounded pool. Operator migration/import connections retain write capability. |
| Browser controls | Restrictive CSP including `script-src-attr 'none'`, anti-framing, nosniff, same-origin resource policy, referrer and permissions policies. HSTS on production HTTPS responses. No permissive CORS configuration, authentication cookies or browser-stored secrets. |
| File exposure | Only the four SPA routes/index and allowlisted compiled asset types under `/assets/` are served. Dotfiles, source maps, arbitrary JSON and paths outside the resolved build directory are rejected. |
| Input/output boundaries | Typed January-only filters, duplicate-query rejection, SQLAlchemy-bound values, escaped React rendering, safe errors and formula-neutralized CSV text remain covered by regressions. No public import, SQL, arbitrary-fetch or mutation endpoint exists. |
| Production configuration | Requires a database password of at least 16 characters and certificate-verified TLS for remote PostgreSQL. Use a random managed secret, not a memorable password. API docs/OpenAPI default off in production; local development keeps them available. |
| Supply chain | Locked dependencies, digest-pinned container inputs, non-root/read-only app containers and reduced capabilities. CI now audits Python and npm lockfiles against advisory feeds. The repository scanner rejects publication of local state and recognized credentials. |

Gzip reduces transfer size for public JSON/CSV and built assets. It does not change the decompressed content used for calculations or download verification. Reassess compression and cache isolation before introducing authenticated or personalized responses.

## Local measurements

The bounded `scripts/load_check.py` tool accepts only loopback HTTP, at most 100 concurrent clients and 2,000 requests. The checks below use the real PostgreSQL-backed monthly January accuracy response, one accepted release and one warmed analysis key, with gzip requested and a new HTTP connection per request. All successful decompressed payload hashes matched within each run.

| Run | Clients / requests | HTTP 200 | Median | p95 | Throughput |
| --- | --- | --- | --- | --- | --- |
| Previous image | 10 / 40 | 40 | 3,263.66 ms | 4,237.20 ms | 2.89 requests/s |
| Updated image | 10 / 40 | 40 | 85.04 ms | 113.78 ms | 100.84 requests/s |
| Updated isolated image | 50 / 200 | 200 | 452.88 ms | 493.35 ms | 107.53 requests/s |

These are short local API bursts, not sustained user-session capacity or an internet SLA. The 50-client test used an isolated Compose project with a **test-only quota of 10,000/minute** so the performance check would not test the normal 120/minute abuse limit instead. The normal local app retains its default quota. Database import, cold starts, diverse uncached filters, external network latency, shared-host quotas and ingress/WAF behavior require separate deployment measurements.

Generated reports live under ignored `output/security-scale/`: `baseline.json`, `after.json`, `load-50.json`, `service.json`, `pytest.xml`, `vitest.xml`, `python-audit.json`, `npm-audit.json` and `browser/browser-report.json`. See [the checked-in evidence summary](security-scale-evidence.json) for the final execution record, including the final disposable-container/restart gate. The local marker is `security-scale-local`; no remote performance claim is made.

## Reproduction

Start the normal local application with `scripts/local.ps1 -Action Start` or `docker compose up --build --detach --wait web`. Compose runs `winddesk seed --configure-reader` before the web process, retaining the database volume. The local defaults are development credentials and loopback-only ports.

For native Python, seed as the operator with `GRID_READER_DATABASE_URL` configured, then set the web process's `GRID_DATABASE_URL` to that separate reader URL. Keep later migrations/imports in a separate operator process. Managed production PostgreSQL may require provisioning these grants through its administration console rather than permitting the helper to create roles.

```text
uv run pytest
uv run ruff check backend scripts
uv run ruff format --check backend scripts
uv audit --frozen --python-version 3.12 --python-platform linux --output-format json
npm audit --prefix frontend
python scripts/verify_service.py
python scripts/verify_security.py
python scripts/load_check.py --users 10 --requests 40
npm run test:browser --prefix frontend
```

Set `GRID_TEST_DATABASE_URL` to a dedicated PostgreSQL test database for the integration suite. The permission test additionally creates/removes a uniquely named test login, so its operator must be able to manage roles. It verifies denied UPDATE/INSERT/DELETE/CREATE and restricted reads even after session read-only mode is disabled. Do not run the suite against production.

Allow the normal rate-limit window to reset between repeated load/service/browser runs, or use a separate disposable test project. Do not weaken the public deployment quota to run a benchmark. `GRID_WEB_WORKERS` supports 1–8 worker processes for non-reload container/native serving; its default is one. Reload mode requires one worker. Each worker has its own cache, pool and quota.

Users behind one office NAT, or behind a proxy whose identity has not been verified, can share a peer quota. Tune limits against concurrent full-page sessions and the hosting ingress before launch; the 50-client API burst is not proof that the default per-peer quota permits 50 simultaneous sessions from the same address.

## Required hosting controls

Application hardening is implemented and locally tested. The following controls require the actual hosting account/infrastructure and are **not configured by this local change**:

1. Serve the public domain through HTTPS and the hosting firewall/WAF. Add managed attack/bot rules, shared request limits, URL/header/body limits, upstream timeouts and appropriate cost/spend alerts. Check the account's plan and pricing before enabling billable features. Use edge rules for volumetric attacks and slow clients; process-local quotas do not provide distributed DDoS protection.
2. Set the exact production and preview hostnames in `GRID_ALLOWED_HOSTS`. Keep docs disabled unless deliberately needed. Verify proxy identity with a real request through the hosting ingress; never accept an arbitrary client's `X-Forwarded-For` as identity.
3. Store the **reader** connection secret in the web service's environment. Run migrations/ingestion as a separate operator job. Use a private/appropriately firewalled database endpoint, verified TLS, secret rotation, managed backups and a tested restore procedure.
4. Set a global connection budget before increasing replicas/functions. Worst-case app connections are `replicas × workers × (pool_size + overflow)`, plus migration/monitoring connections and operational headroom. Defaults are five per Docker process and one per Vercel function instance. The helper caps its reader role at 20 connections; reserve headroom and change that cap deliberately through database administration if a measured workload requires it. For example, three one-worker Docker replicas could consume 15 connections, leaving five reader-role slots; verify the provider's overall limits separately. Use the provider's pooler when appropriate and cap autoscaling accordingly.
5. Review p95/p99 latency, 429/503/500 rates, memory, cache churn and PostgreSQL connections/timeouts. Load-test representative cold/warm filter mixes and sustained traffic on the chosen hosting plan. Adding replicas multiplies cache memory and local quotas; it does not share them. Introduce a shared cache only if measured miss cost justifies its operational overhead, retaining the immutable keys and bounded lifetimes.
6. Keep dependency/container/OS advisories and security regressions in the release process. Review source and deployment permissions, enable repository secret scanning where available and arrange independent penetration testing before treating this pilot as an operational trading system.

No site can be guaranteed immune to every attack. Passing the tests and advisory scans records the controls and known-advisory status at that time, rather than certifying complete security.

## References

Resource bounds follow [OWASP API4: Unrestricted Resource Consumption](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/). Database timeout and read-only settings are described in [PostgreSQL client defaults](https://www.postgresql.org/docs/17/runtime-config-client.html). Hosting rate-limit options must be checked against [Vercel WAF rate limiting](https://vercel.com/docs/vercel-firewall/vercel-waf/rate-limiting). Edge counters may be regional; validate aggregate spending/connection caps separately. Dependency audits use [uv audit](https://docs.astral.sh/uv/reference/cli/#uv-audit) and npm's advisory service. These references describe the mechanisms; the test evidence describes this implementation.
