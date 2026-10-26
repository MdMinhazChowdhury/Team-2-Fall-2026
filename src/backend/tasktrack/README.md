# Backend application

FastAPI routes call the account/task business and persistence modules in this package. SQLAlchemy models use PostgreSQL; every account-owned operation enforces the authenticated owner. `jobs.py` contains Celery configuration and durable recurrence/reminder/mail/export work. Database schema changes live in the sibling `migrations` directory, and tests are under `tests/backend`.
