# Person D Sprint 2 handoff

Open Person-D-Sprint-2-Report.pdf first. The updated project source is in TaskTrack.
The report and CSV tables are also provided in editable form. Evidence contains the
November 15 run logs, screenshots and machine-readable results. Sprint-1-Reference
contains historical evidence and is not a current rerun.

## Changes to apply to the existing repository

The reference checkout is Team-2-Fall-2026, local sprint-1, commit 34f253d.
The GitHub remote could not be contacted in this session; newer teammate changes
have not been compared. Review the patch against your current branch before applying.
No branch was changed, no commit created and nothing pushed.

From the desired repository branch, first use `git status` and:

    git apply --check "PATH/TO/person-d-sprint2.patch"
    git apply "PATH/TO/person-d-sprint2.patch"

If the check fails, reconcile the four changed files with current teammate changes.
The patch modifies TaskEditor.tsx, Workspace.tsx, forms.test.tsx and workflows.spec.ts.
Do not replace a newer repository wholesale with the reference source snapshot.

## Current verification

33 backend/PostgreSQL tests, 9 frontend tests and 8 Chrome/Chromium scenarios pass.
ESLint, TypeScript and the Vite production build pass. Logs are in Evidence.
Component tests mock the request boundary; browser tests call the real API/database.

## Reproduce

Use TaskTrack/README.md for installation, migrations and startup. Use disposable
PostgreSQL databases named tasktrack_test and tasktrack_e2e. Never point fixtures
at a real account database. For the isolated browser API set TASKTRACK_ENV=test,
TASKTRACK_TEST_NOW=2026-10-25T12:00:00Z, TASKTRACK_PUBLIC_ORIGIN=http://127.0.0.1:5173,
TASKTRACK_RATE_LIMIT=500 and TASKTRACK_DATABASE_URL to tasktrack_e2e.
Set TASKTRACK_E2E_DATABASE_URL to the same test database and TASKTRACK_PYTHON to
the test virtual environment interpreter when running Playwright. Then run:

    npm test
    npm run lint
    npm run build
    npx playwright test --project=chrome --project=chromium

For backend tests set TASKTRACK_TEST_DATABASE_URL and PYTHONPATH=src/backend, then
run `pytest tests/backend tests/performance`. Fixed application dates exercise the
original regression fixtures; actual run timestamps are November 15, 2026.
The test-only rate limit prevents rapid fixture setup from exhausting authentication
attempts. Production defaults have not been changed. The first expanded browser run
passed 5 cases and failed 3 on HTTP 429 during fixture setup; the final rerun passed 8.

## Required personal/team entries

Fill Communication-Log.csv with at least three real attempted teammate contacts on
different days. Attach actual email copies as a merged PDF, as the assignment asks.
No teammate messages were sent and no communication evidence was invented.
Complete a real usability session using Usability-Results.csv and the report protocol.
Person A must reconcile the full team's Sprint 1 defect register and obtain backend
transport/release evidence. The report is a Person D contribution, not the combined
Person A final report. No publisher or contributor attribution was added.
