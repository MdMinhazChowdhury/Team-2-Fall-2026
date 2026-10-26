# Database migrations

Versioned Alembic migrations cover the initial account/task schema, recurrence timezone and durable export jobs. From the root run `alembic upgrade head` with the correct database URL. Migration downgrade is destructive and is tested only in disposable schemas. Follow `infra/OPERATIONS.md` before touching real data.
