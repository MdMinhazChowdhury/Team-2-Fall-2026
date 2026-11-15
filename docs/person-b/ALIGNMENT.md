# Person B account-core alignment

Status date: October 26, 2026 (America/New_York).

The supplied Java/SQLite account module was reviewed and adapted to the current Sprint 1 React, FastAPI, and PostgreSQL architecture. Its useful account-factory and administrator behaviors were ported rather than copying a second incompatible application into the repository.

## Implemented mapping

| Supplied module behavior | Current implementation |
| --- | --- |
| User and administrator account types | Account.role with constrained USER and ADMIN values |
| Account enabled/disabled state | Account.active, enforced during login and every authenticated request |
| User factory | AccountFactory, used by public registration and administrator creation |
| Register/login/logout | Existing FastAPI authentication flow, retained with Argon2id and verified email |
| Create/list/disable/enable/delete accounts | Account service plus administrator-only API and React administration screen |
| Initial administrator | Local python -m tasktrack.admin_cli promote EMAIL command |
| Automated testing | Isolated account unit tests and real-PostgreSQL API integration tests |

## Architecture and security choices

The Java classes, Maven structure, SQLite database, IDE metadata, compiled files, and test database were not copied. SHA-256 password storage was also rejected because TaskTrack already uses Argon2id. Account logic now follows the existing route, schema, service, model, migration, and React feature boundaries.

Administrator access is role-checked on the server. Disabling an account revokes its sessions. Administrators cannot disable or delete their own account, and the last active administrator is protected. Administration exposes account metadata only; it does not grant access to another person's task lists, tasks, tags, reports, notifications, history, imports, or exports.

## First administrator

After registering and verifying the first account, run from the project root with the backend environment configured:

    $env:PYTHONPATH='src/backend'
    python -m tasktrack.admin_cli promote admin@example.com

Log out and back in so the Administration navigation item appears.

## Verified local results

- Backend unit, PostgreSQL integration, migration/security, and workload suite: 82 passed.
- Frontend component suite: 8 passed.
- Backend Ruff lint/format and mypy checks: passed.
- Frontend ESLint, Prettier, TypeScript, and production build checks: passed.
- Machine-readable results are saved in the evidence directory.

## Verification scope

tests/unit/test_account_core.py covers factory defaults, normalization, unique IDs, roles, invalid values, schema boundaries, authorization, and response mapping without requiring a database.

tests/backend/test_person_b_accounts.py covers administrator creation/listing, access denial, password hashing, verified creation, disabling and session revocation, login blocking, re-enabling, self-protection, deletion, duplicate email handling, invalid roles, and missing account IDs against isolated PostgreSQL schemas.
