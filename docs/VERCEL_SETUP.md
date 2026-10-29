# Vercel Deployment Preparation

The user confirmed an existing Vercel account on 29 October 2026. Phase 1 prepares a deployable entry point; it does not create a paid database or claim a completed preview deployment.

## Selected route

Use Vercel's FastAPI framework support with the root `app.py` exporting `app`. `vercel.json` runs the locked frontend install and production build, and includes `frontend/dist` in the function bundle. FastAPI serves those files and the API using the same factory tested locally. No experimental multi-service entitlement is assumed.

The Python runtime resolves the root `pyproject.toml` and `uv.lock`, with Python constrained to 3.12. Node 24 is recommended for the React build. Function exclusions and `.vercelignore` omit local environments, tools, caches, source assignment material, research documents, and test artifacts. The frontend dependencies are installed at build time; local `node_modules` is not uploaded.

The local-readiness check verified a staged upload and locked frontend build. Frontend test fixtures stay in the build input because the full TypeScript check includes test modules. `functions.excludeFiles` then omits frontend source/test files and operator helpers from the runtime bundle, retaining compiled `frontend/dist`. Do not exclude only the fixtures from the upload while leaving their importing TypeScript tests behind. Actual Vercel account/runtime/bundle behavior still requires the preview check below.

Official references: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime](https://vercel.com/docs/functions/runtimes/python), and [FastAPI deployment guide](https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel).

## Prerequisites still to verify

- Authenticate the Vercel CLI or import the eventual repository through the account dashboard.
- Confirm project access, runtime/plan eligibility, and any commercial-use conditions for the selected plan.
- Supply an external PostgreSQL database and an approved budget. Use the provider's pooled endpoint if applicable and verify compatibility with psycopg.
- Set the database secret through Vercel environment settings. Do not commit it or put it in a browser-facing Vite variable.
- Run an actual preview deployment and verify frontend assets, API routes, health behavior, and persistence.

## Project configuration

Choose the repository root as the Vercel project root and FastAPI as the framework. Use the checked-in build command. Keep the function-duration setting within the account's allowance. The selected simple architecture serves static files through Python; verify the bundled asset path and bundle size in the preview before considering CDN optimization.

Required external secret:

```text
GRID_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

This is a placeholder, not a working credential. Encode special characters in URL components. `vercel.json` sets the production environment, frontend directory, and a per-instance pool size of one with no overflow. Connection limits still depend on the database tier and the platform's instance concurrency; validate them before operational use.

Optional non-secret configuration includes `GRID_DEFAULT_CUTOFF_LOCAL=09:00` and a deployment commit in `GRID_BUILD_SHA`. The runtime reads `PORT` for local/container serving; Vercel imports `app` directly rather than executing that command.

## Preview smoke test

After authentication and environment setup, deploy a preview and check:

1. `/` loads the compiled React page and fetches `/api/v1/config`.
2. `/health/live` returns 200.
3. `/health/ready` returns 503 until Phase 2 provides an accepted dataset, even if PostgreSQL is reachable.
4. `/api/v1/unknown` returns JSON 404 rather than the React HTML.
5. Static JavaScript and CSS load; secrets are absent from the configuration response and browser bundle.

Dataset persistence, seeding/migrations, and analysis endpoints are verified when their later phases are implemented. An account being available and a configuration file existing do not constitute a successful hosted deployment.
