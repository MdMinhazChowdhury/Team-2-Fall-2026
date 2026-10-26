# Integration testing cases and results

Recorded local runs on October 25, 2026: 33 PostgreSQL-backed cases passed, plus six browser cases (three scenarios in Chrome and three in Chromium). These are additional to the eight frontend unit/component cases, giving 47 automated cases. The separate API process restart probe passed and is not added to that count. Parameterized cases are counted as recorded by JUnit.

## Database and API cases

`PostgreSQL-Test-Cases.csv` lists all 33 exact names and results. Copied tests contain the full inputs and expected assertions. Backend fixtures use real PostgreSQL with disposable schemas. Coverage includes successful writes, invalid names/titles/enums/dates, maximum field lengths, ownership, stale versions and concurrent writers, rollback on failures, session/CSRF/security behavior, migrations, imports, exports, recurrence and reminders.

## Complete browser workflows

| ID | Browser | Scenario | Actual result | Milliseconds |
|---|---|---|---|---|
| B01 | chrome | register, verify, create, edit, filter, complete, reload, cancel delete and restore | passed | 4349 |
| B02 | chrome | responsive controls and automated accessibility at 360, 768 and 1920 pixels | passed | 6139 |
| B03 | chrome | tags, bulk actions, calendar, schedules, reports, preferences and import/export | passed | 7454 |
| B04 | chromium | register, verify, create, edit, filter, complete, reload, cancel delete and restore | passed | 4611 |
| B05 | chromium | responsive controls and automated accessibility at 360, 768 and 1920 pixels | passed | 5854 |
| B06 | chromium | tags, bulk actions, calendar, schedules, reports, preferences and import/export | passed | 6733 |

The primary workflow registers and verifies an account, logs in, creates a list and task, edits fields and checklist, filters and completes the task, reloads and logs in again, verifies saved fields, cancels deletion, and exercises Trash and restoration. A separate probe stops and restarts the API before checking saved data through the UI. The responsive scenario checks 360, 768 and 1920 pixels, validation, keyboard dismissal and automated axe results. The organization scenario exercises tags, bulk completion, calendar, schedules, reports, settings and export/import.

## Performance and supporting checks

Ten concurrent authenticated accounts with 500 tasks each completed 100 measured retrieval/update requests using 25-row pages. The recorded p95 was 0.26424 seconds against a two-second target. This is in-process ASGI with real PostgreSQL; network and proxy time are excluded. The production frontend build, lint, formatting and type checks passed. Runtime dependency audits reported zero known vulnerabilities at execution.

## Verification limits

Firefox 157.0 launch timed out; no Firefox pass is claimed. Docker/Compose, live Redis and Celery transport, live SMTP, staging/production HTTPS, operational alerts and backup/restore rehearsals were not verified. Browser tests read verification tokens from the encrypted test mailbox and invoke the real export worker function directly. Worker function and committed-state tests do not establish broker or mail delivery. Manual accessibility, five-volunteer usability and a second-developer setup review remain outstanding. Final rubric points are assigned by the instructor.
