# Dependency and environment record

Recorded October 25, 2026. Exact dependency graphs are in `requirements.lock`, `requirements-dev.lock` and `package-lock.json`; installed versions were resolved from the registries, compiled and exercised locally.

- Python 3.14.4; FastAPI 0.162.0; SQLAlchemy 2.1.6; psycopg 3.3.6; Alembic 1.20.1; Argon2-CFFI 25.1.0; Celery 5.6.3; cryptography 50.0.2.
- Node 24.15.0; React 19.3.1; TypeScript 6.0.3; Vite 8.3.5; Tailwind 4.3.3; TanStack Query 5.104.5; Playwright 1.64.1.
- Real native PostgreSQL 18.6, downloaded through PostgreSQL's linked EDB binary distribution, running only on local loopback for isolated tests.
- Installed Chrome 155.0.8059.85 and Playwright Chromium 156.0.8078.4 ran the browser suite. Playwright Firefox 157.0 failed to launch; it is not verified.

Official references checked during setup:

- [FastAPI releases](https://fastapi.tiangolo.com/release-notes/)
- [SQLAlchemy PostgreSQL/psycopg dialect](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html)
- [Vite prerequisites](https://vite.dev/guide/)
- [React versions](https://react.dev/versions)
- [TanStack Query installation](https://tanstack.com/query/latest/docs/framework/react/installation)
- [Tailwind Vite integration](https://tailwindcss.com/docs/installation/using-vite)
- [PostgreSQL Windows distribution](https://www.postgresql.org/download/windows/) and [EDB binaries](https://www.enterprisedb.com/download-postgresql-binaries)
- [Celery supported platforms](https://docs.celeryq.dev/en/latest/getting-started/introduction.html), including the native Windows limitation

These are observed/tested pins, not a claim that every component is the newest release. Compose image tags and GitHub Actions major tags still require production digest/SHA review. Docker, live Redis/Celery transport and container-image security scanning were not available on this host. The pinned runtime package audits are saved under `docs/evidence`.
