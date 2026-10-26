# Person D test cases and results

The complete requirement/test mapping is in [verification](../verification.md). Actual run outputs and XML/JSON are in [evidence](../evidence/).

- 33 passing PostgreSQL cases: registration/verification/recovery/session rotation; password and secret hashing; CSRF/origin/headers/rate limits; validation/boundaries; private list/task ownership; all status/priority/checklist edits; task moves and conflicts; confirmation/Trash expiry/restoration; tag operations; atomic bulk rollback; exact dashboard/filter/page/report data; import preview/limits/rollback/single-use; durable export creation/download/isolation; recurrence month-end/retry deduplication; reminders/notifications; bounded encrypted-mail retries; DST gap/ambiguity rules; commit-failure redaction; session revocation; account cascades; upgrade/downgrade/metadata checks; concurrent writers; and the ten-account, 500-task workload.
- 8 passing frontend cases: login credential preservation, corrective errors/retry, registration password constraints, token-fragment handling, task fields/checklist reorder/tag/status/priority persistence requests, error input retention, cancel/delete-checklist behavior, and account-timezone date boundaries.
- 6 passing browser cases: the full register/verify/login/task-edit/filter/complete/reload/relogin/Trash workflow; 360/768/1920 viewport and axe checks; and tags/bulk/calendar/schedules/report/preferences/export/import. Each scenario ran in both installed Chrome and Chromium.
- Additional standalone process-restart verification passed; see `../evidence/api-restart.json` and `screenshots/api-restarted.png`.

These counts exclude Firefox (launch timed out), Docker/Redis/SMTP transport, production/staging exercises, volunteer usability and manual accessibility. Test-only mailbox/export processing uses the real worker functions in isolated PostgreSQL and does not certify broker delivery.
