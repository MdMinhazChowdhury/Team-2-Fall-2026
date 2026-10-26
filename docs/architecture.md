# TaskTrack Architecture Proposal

## Architectural style

TaskTrack will use a modular monolith. The React frontend, FastAPI backend, background worker, PostgreSQL database, Redis broker, and same-origin reverse proxy are separately runnable processes, but the application remains one product and one backend codebase. This keeps development and deployment understandable for a student team while preserving clear module boundaries.

Microservices are explicitly out of scope unless measured scaling or ownership constraints later demonstrate a need.

## Context and containers

1. **Browser client.** React, TypeScript, Vite, Tailwind CSS, accessible reusable components, and TanStack Query.
2. **Web API.** FastAPI application that owns authentication, authorization, validation, business rules, transactions, and API responses.
3. **Background worker.** Celery worker for recurrence generation, reminder delivery, email attempts, export generation, and cleanup jobs.
4. **PostgreSQL.** System of record for accounts, sessions, tasks, schedules, reminders, notifications, activity, imports, exports, and job idempotency.
5. **Redis.** Broker for durable worker delivery and retries. Business truth and deduplication state remain in PostgreSQL.
6. **Reverse proxy.** Same-origin production entry point that terminates HTTPS, serves the frontend, and proxies API requests.
7. **Email provider.** External provider used only through a backend adapter. Development defaults to disabled or a local test sink.

## Frontend boundaries

The `src/frontend` directory will contain:

- `app`: application bootstrap, providers, global error handling, and query client
- `routes`: route definitions, layouts, and access guards
- `features`: account, lists, tasks, dashboard, search, calendar, tags, reports, settings, Trash, import, and export
- `components`: accessible shared visual and form components
- `api`: typed request functions and response contracts
- `utilities`: dates, formatting, validation helpers, and test factories

Feature modules may import shared components and API contracts but should not reach into another feature's internal implementation.

## Backend boundaries

The `src/backend/tasktrack` package will contain:

- `api`: HTTP routes, dependencies, request context, and response mapping
- `config`: typed environment configuration
- `security`: passwords, sessions, CSRF, token hashing, and authorization helpers
- `db`: engine, sessions, transaction utilities, and migration integration
- `models`: SQLAlchemy persistence models
- `schemas`: request and response validation
- `services`: business use cases and account ownership enforcement
- `jobs`: worker tasks, schedules, retries, and idempotency
- `adapters`: email, object storage if required, and external integrations
- `observability`: logging, request identifiers, health, and metrics

Routes remain thin. Business rules and transactions belong in services. Persistence details do not leak into frontend contracts.

Task construction is centralized in `factories.TaskFactory`. `services.save_task` checks list/tag ownership before calling the factory and persists checklist/tag/activity records in the request transaction. Imports reuse that service. Recurring instances use the factory's recurring policy, retaining the rule/occurrence uniqueness key and resetting status to To Do. `filters.TaskFilter` builds the owned task query; the task API authorizes referenced lists/tags and applies existing sorting and pagination. These classes adapt the earlier task-core design to this backend without adding another application or language bridge.

## Authentication and sessions

- Authentication is server-managed rather than browser-stored bearer tokens.
- Passwords use Argon2id through a maintained library.
- The browser receives an opaque, Secure, HttpOnly, SameSite cookie.
- Only a hash of the session secret is stored.
- State-changing requests require CSRF protection.
- Email verification and recovery tokens are random, single-use, hashed at rest, scoped, and expiring.
- Session revocation and account deletion invalidate all active sessions.

## Ownership enforcement

Every account-owned table includes an owner identifier directly or through a constrained parent. Services load records within the authenticated owner's scope. Endpoints do not authorize by trusting object identifiers supplied by the browser. Negative account-isolation tests cover read, update, delete, bulk, export, notification, and history operations.

## Dates, timezones, and clocks

- Calendar dates such as a task due date are stored as date values when no time-of-day exists.
- Events and audit timestamps are stored as timezone-aware UTC timestamps.
- Each account stores an IANA timezone.
- Reminder inputs are interpreted in the account timezone and converted to UTC for execution.
- Recurring schedules preserve their local calendar intent through daylight-saving changes.
- Tests use a controllable clock rather than the machine's current time.

## Concurrency and transactions

Mutable task records carry a version number. Updates use optimistic concurrency and return a conflict response when the submitted version is stale. Bulk actions, imports, recurring-instance creation, and multi-record account operations run in database transactions.

## Soft deletion and Trash

A deleted task receives `deleted_at` and `purge_after` timestamps. Normal queries exclude deleted rows. Restore clears both fields if the parent list remains valid. A scheduled cleanup permanently deletes expired Trash records. Permanent deletion and cleanup record activity without retaining private task content unnecessarily.

## Recurrence and reminders

Recurring definitions are separate from generated task instances. Each generated instance has a database uniqueness key based on the recurrence rule and intended occurrence. The worker may retry safely because insertion is idempotent.

Reminder eligibility and delivery are represented in PostgreSQL. Unique constraints and delivery keys prevent duplicate in-app notifications. Email delivery uses retry limits and records outcomes without storing email secrets.

The background mechanism decision is documented in ADR-0002.

## Imports and exports

Exports are generated from an account-scoped snapshot. Imports use a versioned TaskTrack format. The server applies file and record limits, validates the entire file, produces a preview, and applies the approved import in one transaction. Invalid or partially persistable files make no changes.

## Database migrations and recovery

Alembic migrations are versioned with the backend. Migration upgrades and downgrades are rehearsed in staging before release. Backups target a recovery point within 24 hours. An isolated restoration exercise measures actual recovery point and restoration time before handoff.

## Accessibility and responsive behavior

Shared components define accessible labels, keyboard behavior, visible focus, validation messaging, and contrast. The interface supports 360 through 1920 pixel widths without horizontal page scrolling. Dense calendar views switch to an agenda-style small-screen presentation. Automated checks support, but do not replace, keyboard and screen-reader-oriented manual review.

## Observability and operations

Requests receive identifiers propagated into structured logs and worker messages. Health checks distinguish application readiness from basic process liveness. Configurable alerts cover service failures, repeated job failures, and failed backups. Secrets enter through the runtime environment and are never committed.

## Delivery architecture

Development and test environments will use a root Compose entry point. Production will use a same-origin reverse proxy with HTTPS. GitHub Actions will run formatting, linting, type checks, tests, builds, migration checks, and security scans before release approval.

## Dependency policy

Exact versions are intentionally not invented during planning. During Phase 2, the team will verify supported stable versions against official project documentation, commit manifests and lockfiles, record the decision date, and confirm compatibility in CI.
