# TaskTrack Task Management Application

TaskTrack implements the repository's React/TypeScript/FastAPI/PostgreSQL design. Application code lives under `src`, automated tests under `tests`, documentation/evidence under `docs`, and deployment files under `infra` with the root Compose entry point. This is the web implementation; useful account and task behaviors from the earlier Java/JavaFX/SQLite work are adapted to this architecture rather than duplicated as a second application.

## Features

- Registration, email verification/recovery, Argon2id passwords, opaque hashed sessions, CSRF protection, logout, session revocation, password changes and account deletion.
- Role-based account administration for creating, listing, enabling, disabling and deleting accounts, with session revocation and last-admin safeguards.
- Private lists and tasks with descriptions, dates, priorities, status/reopening, checklists, tags, combined filters, sorting, pagination and bulk actions.
- Confirmed deletion, 30-day Trash recovery, permanent deletion and optimistic task/list versions.
- Dashboard, monthly/weekly calendar, completion-event reports, activity history and timezone/preferences settings.
- PostgreSQL-backed recurrence/reminder schedules, unique occurrence/delivery keys, in-app notifications, optional email, encrypted email outbox, bounded retries and Celery/Redis scheduling.
- Background export jobs with account-scoped downloads, plus versioned import validation, preview, limits and transactional application.

The implementation and local verification are recorded in [progress](docs/progress.md), [requirement evidence](docs/verification.md), [Person B account alignment](docs/person-b/ALIGNMENT.md), and [Person D report](docs/person-d/REPORT.md). The [Person C alignment notes](docs/person-c/ALIGNMENT.md) map the current task core to the supplied Sprint 1 logic-developer rubric and distinguish this update from the inherited application. These records separate verified local checks from outstanding release and submission requirements.

Account creation uses `AccountFactory` for both public registration and administrator-created accounts. Administrator operations are isolated in an account service and account-metadata API; they never expose another user's task data. Task creation uses `TaskFactory` in the existing backend for API creation, imports, and recurring instances. `TaskFilter` builds the account-scoped query shared with the existing task endpoint. The UI contract remains UUID IDs, `list_id`, `TODO`, and 30-day Trash; there is no second Java service to connect.

## Start with Docker Compose

Requirements: Docker with Linux containers and Compose. This workstation did not have Docker, so container startup remains unverified here; the API/UI were tested natively against PostgreSQL 18.6.

1. Copy `.env.example` to `.env`.
2. Replace `POSTGRES_PASSWORD` with a URL-safe random password. Generate an independent session secret of at least 48 random characters and set `TASKTRACK_SESSION_SECRET`. Generate `TASKTRACK_EMAIL_KEY` using `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` after installing Python dependencies.
3. Keep `TASKTRACK_PUBLIC_ORIGIN=http://localhost:8080` for this development stack.
4. Run `docker compose up --build`.
5. Open http://localhost:8080. Register, then open the verification email in development Mailpit at http://localhost:8025. The worker and scheduler must be running to deliver mail, recurrence, reminders and exports.

The migration job runs before the API. PostgreSQL and Redis use named volumes. The supplied stack is local HTTP development configuration. Production prerequisites and safe upgrade/rollback/backup procedures are in [operations](infra/OPERATIONS.md). Do not use a destructive migration downgrade against real data.

## First administrator

Register and verify an account, configure the backend environment, then run `python -m tasktrack.admin_cli promote admin@example.com` with `PYTHONPATH=src/backend`. Log out and back in to refresh the account metadata and open the Administration screen.

## Native development and tests

Use Python 3.14 and Node 24.15 (the versions tested here). From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
npm.cmd ci
$env:PYTHONPATH='src/backend'
$env:TASKTRACK_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/tasktrack'
$env:TASKTRACK_PUBLIC_ORIGIN='http://127.0.0.1:5173'
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn tasktrack.main:app --host 127.0.0.1 --port 8000
# In a second terminal in this directory:
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Provide SMTP and run Celery/Redis in Linux containers/WSL for ordinary native-development registration, scheduling and background exports. Celery does not support native Windows workers. Test fixtures can inspect only their own isolated test mailbox; they are not a production email mechanism.

Automated checks:

```powershell
$env:TASKTRACK_TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/tasktrack_test'
.\.venv\Scripts\pytest.exe tests/unit tests/backend tests/performance --junitxml=docs/evidence/backend-results.xml
.\.venv\Scripts\ruff.exe check src/backend tests
.\.venv\Scripts\ruff.exe format --check src/backend tests
.\.venv\Scripts\mypy.exe
npm.cmd run lint
npm.cmd run format:check
npm.cmd run build
npm.cmd test
```

Tests require a disposable PostgreSQL database where the test user may create/drop isolated schemas; they never fall back to SQLite. Browser tests require a separate database named `tasktrack_e2e`, migration upgrade, API and Vite servers, and installed Playwright browsers. Set `TASKTRACK_E2E_DATABASE_URL`, `TASKTRACK_ENV=test`, `TASKTRACK_TEST_NOW=2026-10-25T12:00:00Z`, and matching `TASKTRACK_PUBLIC_ORIGIN` in the API process; run `npx playwright install chromium firefox` and `npm run test:e2e`. On Linux set `TASKTRACK_PYTHON=python` after activating the virtual environment. A fixed clock is refused outside test mode. Browser fixtures read verification messages and process export jobs directly in their isolated PostgreSQL database, allowing native UI testing without pretending a Redis worker was tested.

The backend dependency graph is pinned in `requirements.lock`, development tools in `requirements-dev.lock`, and npm dependencies in `package-lock.json`. CI is configured in `.github/workflows/ci.yml`, including the isolated core tests. Local success does not establish a passing remote CI run.

To run only the isolated factory/service tests without PostgreSQL, use `.\.venv\Scripts\pytest.exe --confcutdir=tests/unit tests/unit`. The `--confcutdir` option excludes the database-specific parent fixtures. The same tests are also included in the full PostgreSQL suite and CI. `.gitattributes` preserves LF text files so the format checks behave consistently on Windows and Linux.

## Behavior and limits

Lists must be empty, including Trash, before confirmed deletion; move or permanently delete their tasks first. Due dates may be absent or in the past. Priority defaults to Medium. Checklists support ordering through the editor's move-up controls. All mutations enforce account ownership on the server, and stale task/list versions return conflicts.

Reminders without an offset use the account timezone. Nonexistent DST times are rejected; ambiguous times require an explicit offset. Recurrence keeps its configured timezone and original monthly day, clamping to month end when necessary. Generated instances start To Do. Email is at-least-once across an SMTP-acceptance crash; in-app reminders and recurrence occurrences use database uniqueness keys.

Exports contain active lists/tasks/checklists/tags, excluding schedules, reminders, activity and Trash. Supported limits: 2 MiB, 100 lists, 500 tags and 5,000 tasks. Export jobs expire after one hour. Import previews expire after 15 minutes, require explicit application, and apply atomically. Matching tag names are reused; imported lists/tasks are new records. The read-only `/api/export` snapshot endpoint remains for integration compatibility; the UI uses background export jobs.

## Release checks still required

Firefox launch timed out in the inherited verification record. Docker/Redis/Celery transport and restart integration, live provider email, production HTTPS/alerts, staging deployment, backup restoration, five-volunteer usability study and second-developer setup/signoff remain unverified. See the evidence matrix rather than treating source presence as release approval.
