# Infrastructure

Root `compose.yml` connects PostgreSQL, Redis, Mailpit, the migration job, API, worker, scheduler and Caddy/frontend. Dockerfiles and proxy configuration are here. Read `OPERATIONS.md` for startup, production prerequisites, rollback precautions, monitoring and backup/restore checks. Container/production verification remains pending; local native results are in `docs/verification.md`.
