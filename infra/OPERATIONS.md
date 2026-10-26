# Operations and release checks

The root Compose file is for local development. It binds the web app to loopback HTTP and Mailpit to loopback port 8025. It is not a production HTTPS deployment. Run exactly one beat scheduler. PostgreSQL row locks and uniqueness keys protect duplicate worker scans. Workers read committed PostgreSQL outbox records; broker messages contain no email tokens. SMTP can redeliver after a crash following acceptance; deterministic Message-ID is provided. In-app reminders and recurring occurrences have database uniqueness keys.

## Local startup

Install Docker with Compose on a supported host. Copy `.env.example` to `.env`, generate a URL-safe database password and independent random session and Fernet keys, then run `docker compose up --build`. Open http://localhost:8080 and http://localhost:8025 for development email. Register, open the verification message in Mailpit, and follow its link. Celery officially does not support native Windows: use Linux containers/WSL for real queue/worker testing.

## Production prerequisites

Provide approved hosting, DNS/TLS, authenticated SMTP with TLS, protected PostgreSQL/Redis networks, least-privilege database credentials, independent Fernet key, backup storage, and monitoring. Set `TASKTRACK_ENV=production` and `TASKTRACK_PUBLIC_ORIGIN=https://your-domain`. Production configuration rejects HTTP origins, development or short session keys, and absent email keys. Terminate HTTPS at a same-origin reverse proxy with the headers/body-size policy in `Caddyfile` and HSTS. Never expose development Mailpit or unauthenticated Redis. Configure a single trusted proxy before relying on per-client rate-limit addressing; the backend deliberately ignores forwarded headers from arbitrary clients.

Review and pin image digests and GitHub Actions commit SHAs before an approved production release. CI is configured; a successful GitHub run is not claimed until it occurs. Local Compose, Redis delivery/restarts, production HTTPS, provider email and alert routing require a supported container host and credentials and remain release checks.

## Migration and rollback

Back up before changes. Run `alembic upgrade head` as a separate migration job before replacing instances. Verify compatibility in staging. The initial schema's downgrade removes tables: use `alembic downgrade base` only on disposable test databases. A production rollback restores a verified pre-upgrade backup with its matching application release. Automated migration tests upgrade, compare metadata, downgrade and re-upgrade in an isolated schema.

## Backup and isolated restore

Schedule `pg_dump --format=custom` at least daily with protected credentials and encrypted independent storage. Alert on failure or backup age over 24 hours. To rehearse, create a separate empty database, restore with `pg_restore --exit-on-error --no-owner`, run `alembic current`, verify account/task counts, and exercise login/task reads. Record backup timestamp, recovery point, elapsed time and verification results. Targets: RPO <= 24 hours, RTO <= 4 hours. A small local rehearsal does not establish production recovery performance.

## Monitoring

Poll `/api/health/live` and `/api/health/ready`; collect JSON request logs and request IDs. Never log bodies, cookies, tokens or task descriptions. Monitor Celery queue depth, worker availability, scan failures, `outbox.status='failed'`, backup age and database availability. Outbox retries stop after five attempts with exponential backoff. Investigate safe error codes, correct SMTP, then explicitly reset failed entries to pending. Only trusted operators may inspect encrypted mailbox data.

Alert destinations, heartbeat monitoring and backup automation require deployment-specific configuration and verification. No staging deployment, external notification, volunteer test or second-developer signoff is represented as completed.
