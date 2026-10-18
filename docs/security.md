# TaskTrack Security Plan

## Security objectives

TaskTrack must protect account credentials, private task data, sessions, imports, exports, and operational secrets. Security controls are implemented in the server and verified by tests rather than relying on hidden UI controls.

## Threats in scope

- Credential theft and password database compromise
- Session theft, fixation, and unauthorized reuse
- Cross-site request forgery
- Cross-site scripting and unsafe output
- Broken object-level authorization between accounts
- Injection and malformed input
- Abuse of imports, exports, reminders, and bulk operations
- Secret leakage through logs or error responses
- Duplicate or replayed background work
- Accidental data loss and failed recovery
- Dependency and build-chain vulnerabilities

## Authentication controls

- Hash passwords with a maintained Argon2id implementation.
- Apply reasonable password rules and rate limits without storing plaintext.
- Store only hashes of verification, recovery, and session secrets.
- Make verification and recovery tokens random, scoped, expiring, and single-use.
- Rotate the session identifier after authentication and sensitive account changes.
- Support individual and all-session revocation.
- Require recent authentication for password changes and account deletion.

## Session and browser controls

- Use Secure, HttpOnly, SameSite cookies in production.
- Use an independent CSRF token or a well-reviewed framework mechanism for state-changing requests.
- Restrict CORS to the configured same-origin deployment.
- Apply Content-Security-Policy, frame restrictions, MIME sniffing protection, and a suitable referrer policy.
- Do not store authentication secrets in localStorage.
- Escape rendered content and avoid unsafe HTML insertion.

## Authorization and isolation

- Derive account identity only from the validated server session.
- Scope every account-owned query by `account_id`.
- Validate that parent and child records share the same owner.
- Apply ownership checks to bulk actions, searches, calendar feeds, history, notifications, imports, and exports.
- Return non-enumerating not-found or forbidden behavior according to a consistent policy.
- Test cross-account identifiers for every major resource and operation.

## Input and error handling

- Validate type, length, format, enumeration, date range, file size, record count, and pagination bounds.
- Use parameterized ORM operations and carefully reviewed raw SQL only when necessary.
- Reject unsupported import versions and validate the entire file before persistence.
- Return stable problem details without stack traces, secrets, SQL, internal paths, or dependency versions.
- Log error identifiers and safe context rather than private task content.

## Background work

- Keep job intent and idempotency state in PostgreSQL.
- Use unique keys for recurring occurrences and reminder deliveries.
- Bound retries and use exponential backoff with jitter where appropriate.
- Move persistent failures to an inspectable failed state and alert operators.
- Never put passwords, session secrets, full import files, or unnecessary private content in broker messages.

## Data and recovery

- Require encrypted transport to production services.
- Use least-privilege database and broker credentials.
- Store secrets outside the repository.
- Back up PostgreSQL at least often enough to target a 24-hour recovery point.
- Rehearse restoration in isolation and record actual recovery point and restoration time.
- Define retention and secure deletion for exports, logs, Trash, and deleted accounts.

## Verification plan

Automated checks will cover password hashing parameters, token expiry and single use, session rotation and revocation, CSRF rejection, security headers, account isolation, validation, transactional import rollback, concurrency conflicts, and redaction of errors. Manual release checks will review cookie attributes, browser behavior, access-control edge cases, dependency findings, secret scanning, and restore evidence.

## Open decisions

- Final email provider and sender-domain configuration
- Production hosting and managed database provider
- Approved data-retention periods beyond the 30-day task Trash rule
- Rate-limit values based on deployment capacity and test evidence
- Whether export artifacts require external object storage or short-lived database-backed streaming
