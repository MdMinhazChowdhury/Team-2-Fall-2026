# TaskTrack Task Management Application

TaskTrack is a planned web-based personal task management application for students and individual users. It will provide private accounts, task lists, priorities, deadlines, checklists, recurrence, reminders, calendar views, search, filters, bulk actions, activity history, reports, Trash recovery, and validated data portability.

## Current phase

Phase 1: requirements and architecture planning.

No application features have been implemented yet. The repository currently contains the approved requirements, architecture proposal, data model outline, security plan, traceability matrix, implementation backlog, phase plan, and directory placeholders.

## Planned stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query
- Backend: Python, FastAPI, SQLAlchemy, Alembic
- Data: PostgreSQL
- Background work: Celery with Redis as the broker, with PostgreSQL-backed idempotency and outbox records
- Testing: pytest, Vitest, React Testing Library, Playwright, and performance tests
- Delivery: Docker Compose, same-origin reverse proxy, and GitHub Actions

Exact supported dependency versions will be verified against official documentation during the foundation phase before manifests and lockfiles are committed.

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [Security](docs/security.md)
- [Traceability](docs/traceability.md)
- [Implementation plan](docs/implementation-plan.md)
- [Backlog](docs/backlog.md)
- [Progress](docs/progress.md)
- [Architecture decisions](docs/decisions/)

## Repository structure

- `src/frontend`: frontend application source
- `src/frontend/public`: static assets
- `src/backend/tasktrack`: backend application package
- `src/backend/migrations`: Alembic migrations
- `tests/frontend`: frontend unit and component tests
- `tests/backend`: backend unit and integration tests
- `tests/e2e`: cross-application end-to-end tests
- `tests/performance`: performance tests and workloads
- `docs`: requirements, architecture, decisions, progress, and operations
- `infra`: deployment, reverse-proxy, and infrastructure configuration
- `.github/workflows`: continuous integration and release workflows

This keeps all developer-owned application files under the assignment's top-level `src` folder and all testing files under `tests`. The root Compose entry point, dependency manifests, lockfiles, and tool configuration are scheduled for Phase 2 after dependency versions are verified.
