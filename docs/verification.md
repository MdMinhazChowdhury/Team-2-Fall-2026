# Requirement verification index

Local verification date: October 25, 2026 (America/New_York). Governing scope is `requirements.md` and the repository architecture; a separate instructor rubric was not supplied.

## Recorded results

- PostgreSQL API/integrity/security/migration/worker-function/performance suite: **33 passed**, zero failures/skips. See [JUnit XML](evidence/backend-results.xml) and [console output](evidence/backend-console.txt).
- Frontend controls/date tests: **8 passed**. See [console output](evidence/frontend-console.txt).
- Browser acceptance: **6 passed**, three scenarios each in installed Chrome and Playwright Chromium. See [browser report](evidence/browser-results.json), [console output](evidence/browser-console.txt) and [screenshots](evidence/screenshots/).
- Responsive checks: 360/768/1920 pixels, no horizontal document overflow. Automated axe checks passed on task views and the editor dialog. This is not a manual WCAG certification.
- Workload: 10 simultaneous authenticated accounts, 500 tasks each, 100 measured retrieval/update requests, page size 25, real PostgreSQL. The latest [measurement](evidence/performance.json) gives the exact p95 (approximately 0.26 seconds), platform and transport. In-process ASGI testing excludes network/proxy time and does not certify production capacity.
- TypeScript production build, ESLint, Prettier check, Ruff lint/format and mypy passed. See [build output](evidence/build-console.txt) and [quality checks](evidence/quality-checks.txt).
- Runtime Python and npm audits reported zero known vulnerabilities at execution; see [Python audit](evidence/python-audit.json) and [npm audit](evidence/npm-audit.json). This is not a security guarantee.
- Firefox 157.0 was installed but launch timed out. See [launch evidence](evidence/firefox-launch.txt); no Firefox pass is claimed. Browser versions are recorded in [environment](evidence/environment.json).

## Functional test mapping

| Requirement | Implemented path and passing local evidence | Remaining qualification |
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

## Nonfunctional and objective status

NFR1/NFR2/NFR6/NFR8/NFR15 have local code/test evidence for hashing/isolation, transactional writes, rollback, limits and redaction. NFR3 cookie/CSRF/header controls are tested, but actual production HTTPS is pending. NFR4 and automated portions of NFR7 have local viewport/axe evidence; manual accessibility remains. NFR5 has the bounded workload above. NFR9 has installed Chrome coverage; Firefox remains open. NFR10 has structure, lockfiles and migration checks; second-developer setup is still pending. NFR11 has committed-state/deduplication/function retry tests and configuration; broker/process verification remains. NFR12 restoration and production RPO/RTO evidence are absent. NFR13 JSON logs, request IDs and health checks exist; deployment-specific alerts/heartbeat/backup monitoring remain. NFR14 checks pass locally and CI is configured; no remote CI run or container image scan is claimed.

O1 remains pending complete release acceptance, O2 requires five real volunteers, O3 has local fixed-dataset evidence, O4 has local security/concurrency/import/performance evidence but awaits transport/deployment completion, and O5 requires a real second developer and deployment/restore rehearsals. Source presence is not a substitute for these records.

## Reproduction and test isolation

Use the root README commands. Backend fixtures create/drop only randomly named schemas in the explicitly selected PostgreSQL test database. Browser fixtures require `tasktrack_e2e`. Application and browser clocks are fixed only in test mode; artifact timestamps and workload timing use the real wall/performance clocks. Dependency/format/type checks do not require modifying real user data.

Additional persistence evidence: the API was stopped and relaunched, then an existing test account logged in through the UI and its saved description, deadline, completed status and checklist were verified. See `evidence/api-restart.json` and `evidence/screenshots/api-restarted.png`.
