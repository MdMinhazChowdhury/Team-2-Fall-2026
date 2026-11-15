# Sprint 2 Security Backend Handoff

Dennis Grodzicki | Person B | November 15, 2026

## Scope

Person C (Eli) covered the performance requirement. This update covers the security requirement for the account and administrator backend: password storage (NFR1), server-side authorization and account isolation (NFR2), and sessions, cookies, CSRF and headers (NFR3). It also adds API/service and database tests for the account and administrator endpoints, fixes one security defect found by the new tests, and restores Sprint 1 documentation that was never committed.

## Backend change

**Defect found and fixed: unlimited current-password guessing.** Login and recovery (`POST /api/auth/*`) were rate limited, but the signed-in routes that check the current password were not: `POST /api/me/password` (change password) and `DELETE /api/me` (delete account). Someone holding a stolen session cookie could guess the account's password without limit and then change it or delete the account. `main.py` now applies the same per-client limit (20 attempts per minute by default) to those two routes through `is_rate_limited()`. Responses, the frontend contract, and the database schema are unchanged.

The two regression tests for this defect fail on the previous code (400 on every guess, never 429) and pass with the fix.

## Defect status entries for the shared table

| Item | Owner | Status | Verification |
| --- | --- | --- | --- |
| Current-password checks on change-password and delete-account were not rate limited | Person B | Fixed | `test_current_password_guessing_is_rate_limited` (2 cases): 429 by the sixth attempt with a limit of 5 |
| Sprint 1 Person B documentation and admin-role doc updates missing from the repository (the docs upload of Oct 26 did not complete) | Person B | Fixed | `docs/person-b/`, `docs/architecture.md`, `docs/data-model.md`, `docs/progress.md` and the Person C cross-reference restored |
| Dependency scan (`pip-audit`, CI) failed on sprint-2: dnspython 2.9.0 (CVE-2026-128089) and opentelemetry-api 1.45.1 (CVE-2026-126360) | Person B | Fixed | Locked to dnspython 2.9.2 and opentelemetry-api 1.45.2 in both lock files; `pip-audit -r requirements.lock` reports no known vulnerabilities, `npm audit --audit-level=high` passes, all 115 tests pass |
| `docs/requirements.md` (FR1–FR20) does not list the administrator role that the code now implements | Person A (requirements owner) | Deferred | Team decision needed on adding an administrator requirement |

**Defect found and fixed: vulnerable dependencies.** The CI dependency scan failed on sprint-2 (including the Person C Sprint 2 commit) because two locked Python packages had published vulnerabilities. Both were updated to their fixed patch releases in `requirements.lock` and `requirements-dev.lock`. No code changes were needed.

## Security tests (tests/backend/test_person_b_security.py, real PostgreSQL)

| Requirement | Test | Expected | Result |
| --- | --- | --- | --- |
| NFR1 | Password storage | Argon2id, m=65536 KiB, t=3, p=4; plaintext never stored | Pass |
| NFR1 | Hashing cost (measured) | Each guess costs 20–1000 ms | Pass, 118.9 ms median (about 8 guesses/second/core) |
| NFR1 | Session secret storage | Only a 64-character SHA-256 hash of the cookie is stored | Pass |
| NFR3 | Cookie flags and headers | HttpOnly, SameSite=Lax; DENY framing, nosniff, no-referrer, CSP frame-ancestors 'none' | Pass |
| NFR3 | Session fixation | Login replaces any existing session cookie; one session row remains | Pass |
| NFR3 | Expired and logged-out sessions | Both rejected with 401, including a reused stolen cookie | Pass |
| NFR3 | CSRF (3 routes) | Admin create, change password, delete account refused without token and with origin only | Pass |
| NFR2 | Admin routes (4 routes) | 401 when anonymous, 403 for a regular user; target account unchanged | Pass |
| NFR2 | Privilege escalation (3 fields) | `role`, `active`, `verified_at` rejected on register and preferences; no admin created | Pass |
| NFR2 | Isolation | An administrator cannot read another user's task or task list or revoke their session | Pass |
| NFR2 | Injection-style input (3 inputs) | 401/422, never 500; account and task tables unchanged | Pass |
| Brute force | Login | 429 by the sixth attempt with a limit of 5 | Pass |
| Brute force | Current-password checks (2 routes) | 429 by the sixth attempt with a limit of 5 | Pass after fix |
| Enumeration (measured) | Login timing | Unknown email within 0.5×–2× of a wrong password for a real account | Pass, 131.7 ms vs 131.5 ms median |

## API/service and database tests (tests/backend/test_person_b_api_db.py)

| Type | Test | Expected | Result |
| --- | --- | --- | --- |
| API | Response shape | id, email, role, active, timezone, email_reminders only; no password or hash text | Pass |
| API | Status and delete codes | 200 with updated body; 204 with empty body | Pass |
| API | Missing, malformed, duplicate | 404 for unknown or non-UUID IDs; 409 for duplicate email (any case) | Pass |
| API | Validation | 422 for unknown role, 11-character password, bad email, unconfirmed or missing delete confirmation, non-boolean status | Pass |
| API | Administrator protection | A second admin can be deleted; deleting yourself as the remaining admin returns 409 | Pass |
| Database | Account CRUD round trip | Create, read (API and row), update preferences and password hash, delete removes the row | Pass |
| Database | Cascade | Deleting an account removes only its lists, tasks and sessions; another account's task remains | Pass |
| Database | Uniqueness | The database itself rejects a second account with the same email | Pass |

## Regression

| Check | Result |
| --- | --- |
| All Python tests: Sprint 1 unit, API, authorization, database, migrations, workload, Person C Sprint 2, and these 32 new cases | 115 passed, 0 failed, 0 skipped |
| Ruff lint, Ruff format, mypy | Passed |
| Dependency audit: `pip-audit -r requirements.lock`, `npm audit --audit-level=high` | No known vulnerabilities after the update |
| Frontend | Not rerun here; no frontend files changed |

Run on local PostgreSQL 16 with Python 3.13 on Linux, in-process ASGI client (no browser, network or proxy). Reproduce with a disposable PostgreSQL database in `TASKTRACK_TEST_DATABASE_URL` and run `pytest tests/unit tests/backend tests/performance`. Evidence: `evidence/person-b-security-results.xml` (includes the recorded timing values) and `evidence/person-b-regression-console.txt`.

## For the architecture diagram

The security checks sit in front of the routes: the request middleware (`main.py`) enforces the body-size limit, rate limits, and security headers; `security.py` dependencies resolve the session, CSRF token, active account and administrator role before any route runs; `account_services.AccountService` applies the administrator business rules; data access stays scoped to the signed-in account.
