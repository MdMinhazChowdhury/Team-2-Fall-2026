# Functional integration report

The current repository implements the React, FastAPI and PostgreSQL web specification. React forms call the typed fetch client asynchronously; FastAPI routes validate inputs and use SQLAlchemy models and service functions against PostgreSQL. Browser database operations occur on the server, and queued exports and schedule work use worker functions. The interface awaits requests and displays failures without synchronous database work on the browser thread.

The earlier Java AccountService, TaskService and SQLite request belongs to a separate desktop deliverable. Those classes are not the architecture of this web repository. This package reports the current web implementation and does not claim Java or SQLite integration here. Lists are the web specification's task containers. No separate administrator role or admin screen is claimed by this report.

Integration points: `src/frontend/api/client.ts` connects controls to `api.py`, `task_api.py` and `extras_api.py`. `security.py` resolves the current account and session; owner checks in `services.py` scope records to that account. `models.py` and `db.py` persist transactions. `jobs.py` and `adapters.py` implement scheduled work and mail/export processing. Migrations are in the backend Alembic directory. All paths are relative to the repository root.

| Requirement | Implemented integration and passing local evidence | Qualification |
|---|---|---|
| FR1 | Auth UI; register/verify/login/logout/forgot/reset APIs; hashed-secret/single-use/recovery tests; browser workflow | Browser fixture reads the encrypted test mailbox. Live SMTP transport remains unverified. |
| FR2 | List create/rename/version/confirmed-delete tests; browser list creation | Nonempty lists, including Trash, are deliberately blocked from deletion. |
| FR3 | Required title and optional description/date; parameterized validation/boundaries; browser creation | Server validates independently of HTML constraints. |
| FR4 | Full task edit/move; stale-version conflict test; browser edit/persistence | Multiple concurrent writers tested for one winner and one conflict. |
| FR5 | Confirmed Trash, 30-day expiry, restore, permanent delete; browser cancellation/restore | Purge function tested through worker services, not Redis delivery. |
| FR6 | To Do/In Progress/Completed/reopen; API transition/activity tests; browser completion | Completion events remain in reports after reopening. |
| FR7 | Low/Medium/High with Medium default; API and frontend form tests | None specific beyond remaining release checks. |
| FR8 | Fixed-clock dashboard dataset and browser summary | Uses account timezone; completed tasks excluded from due categories. |
| FR9 | Combined owner-scoped search/list/status/priority/tag/due filters; API dataset and browser filters | Title searches escape literal wildcard characters. |
| FR10 | Due/priority/newest ordering and pagination; API boundaries; UI selectors | Load measurement uses 25-row pages. |
| FR11 | Checklist create/edit/reorder/complete/delete via task editor; frontend/API/browser tests | Checklist changes are saved with the parent task version. |
| FR12 | Daily/weekly/monthly rules, anchored month end, end dates, stored timezone; repeated worker-function scans and browser schedule creation | Real Celery/Redis process restart/retry remains unverified on this Windows host. |
| FR13 | Reminder eligibility, local time/DST validation, unique notifications, email outbox/retry; API/function tests; browser schedule creation | Real SMTP and Redis transport remain unverified. SMTP is at-least-once; in-app delivery is deduplicated. |
| FR14 | Monthly/weekly calendar and small-screen agenda; dated range query API; browser calendar task opening | Browser screenshot matrix covers task views; manual calendar screen-reader review remains. |
| FR15 | Unique personal tags, rename/delete/assignment; API and browser tests | All tag links require the same owner. |
| FR16 | Atomic complete/move/priority/Trash bulk API; rollback test; browser bulk completion | Selection capped at 100 tasks. |
| FR17 | Account-scoped creation/edit/completion/reopening/restoration history; API assertions and task history UI | History exposes event/field names rather than private snapshots. |
| FR18 | Durable export job, repeatable-read worker snapshot, owner download, bounded format; validated preview/apply; rollback/single-use tests; browser round trip | Browser harness directly invokes the real export worker function; no broker transport claim. |
| FR19 | Completion-event reports plus current status counts; fixed dataset/reopening history tests; browser report | Reopening does not erase earlier completion events. |
| FR20 | Timezone/notification settings, password change/rotation, individual/all-session revoke, account deletion cascade; API and browser settings | User-supplied current password is required for password change/deletion. |
