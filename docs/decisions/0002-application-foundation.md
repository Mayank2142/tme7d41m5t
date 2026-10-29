# Application and Hosting Foundation

Status: application architecture adopted; user selected an existing Vercel account; authenticated hosting, external PostgreSQL, and cost ownership pending.

Use a modular FastAPI service with synchronous SQLAlchemy/psycopg database access, a small bounded PostgreSQL connection pool, and an operator CLI. React and TypeScript use Vite for development and a compiled static build for single-origin serving from FastAPI. Both dependency ecosystems have committed locks.

Keep process liveness independent of PostgreSQL. Readiness requires a reachable database and an accepted dataset release. During Phase 1, even a successful database probe returns `NO_ACCEPTED_DATASET`; application configuration remains readable so the UI can communicate the missing prerequisite.

Use Docker Compose for local PostgreSQL and the combined application image. The Dockerfile uses pinned language major/minor versions and a versioned uv binary. Image digest pinning, image scanning, migrations, seed initialization, and CI are finalized and exercised in later phases. Development credentials are explicit local defaults and must be replaced for a hosted production environment.

The user confirmed an existing Vercel account during Phase 1. The selected route is a recognized root `app.py` exporting FastAPI, with a Vercel build command compiling React and including `frontend/dist` in the function bundle. The same FastAPI factory serves the frontend and API. This supports one origin without depending on the platform's multi-service beta. Static CDN optimization can be revisited after an actual preview validates the base path.

Vercel uses external PostgreSQL with a small per-instance connection pool. The database engine is initialized lazily at app creation rather than exclusively in ASGI lifespan, so readiness can run on function adapters. An authenticated account, plan eligibility, database entitlement, budget owner, and actual costs must be confirmed before hosting readiness is marked complete. No paid resource, remote repository, or public application is created by Phase 1. The manifest alone is not proof of deployment; an external preview smoke test remains necessary. The existing Heroku manifest is an alternative artifact rather than the chosen target.
