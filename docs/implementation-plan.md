# TaskTrack Implementation Plan

## Release sequence

The complete scope is large for a student team. Requirements remain approved and traceable, but delivery should proceed in controlled increments.

- **Release A, secure core:** FR1-FR7, FR11, FR20 account and session basics; NFR1-NFR3, NFR6, NFR8, NFR10, NFR14.
- **Release B, organization and insight:** FR8-FR10, FR14-FR16, FR19; NFR4, NFR7, NFR9.
- **Release C, automation and portability:** FR12, FR13, FR17, FR18 and remaining operations requirements.
- **Final verification and handoff:** all approved requirements and O1-O5 evidence.

Deferral between releases must be explicit. No requirement is silently removed.

## Phase 1 Requirements and architecture

**Requirements addressed:** FR1-FR20, NFR1-NFR15, O1-O5 at planning level.

**Dependencies:** Approved assignment scope and team review.

**Deliverables:** Requirements, architecture, data model, security plan, ADRs, traceability, backlog, progress record, and repository structure.

**Acceptance criteria:** Exactly five objectives are present; all requirements have IDs and planned evidence; architecture addresses the required security, date, concurrency, deletion, recurrence, reminder, import, migration, recovery, accessibility, and operational concerns.

**Verification:** Document review and repository-structure inspection.

**Risks and external prerequisites:** Team approval, hosting constraints, course deadlines, and unresolved provider decisions.

## Phase 2 Foundation and data model

**Requirements addressed:** NFR6, NFR8, NFR10, NFR13, NFR14 and foundations for all FRs.

**Dependencies:** Approved architecture; verified supported dependency versions.

**Deliverables:** Frontend and backend scaffolds, manifests and lockfiles, Compose, reverse proxy, PostgreSQL, Redis, SQLAlchemy models, Alembic migrations, configuration, structured logging, request IDs, health checks, and CI.

**Acceptance criteria:** A fresh checkout starts locally; migrations upgrade and downgrade; frontend and API health endpoints pass; CI performs formatting, linting, types, tests, builds, migration checks, and applicable security scans.

**Verification:** Fresh-checkout rehearsal, migration tests, CI run, and configuration review.

**Risks and external prerequisites:** Dependency compatibility, container tooling, developer operating systems, and CI availability.

## Phase 3 Authentication and account security

**Requirements addressed:** FR1, account-security portions of FR20, NFR1-NFR3, NFR8.

**Dependencies:** Account/session schema, email adapter interface, reverse-proxy security design.

**Deliverables:** Registration, verification, login, logout, recovery, Argon2id passwords, opaque sessions, CSRF protection, session management, password change, timezone and notification settings.

**Acceptance criteria:** Secrets are hashed; tokens expire and are single-use; sessions rotate and revoke; cross-account access fails; secure cookie and error policies are enforced.

**Verification:** Unit, integration, browser, abuse, account-isolation, and configuration tests.

**Risks and external prerequisites:** Email provider configuration, sender-domain approval, and secure production secrets.

## Phase 4 Core task management

**Requirements addressed:** FR2-FR7, FR11, initial FR17, NFR2, NFR6-NFR8.

**Dependencies:** Authenticated account context, migrations, shared accessible components.

**Deliverables:** Lists, tasks, priorities, status transitions, checklist items, optimistic concurrency, Trash, restoration, purge rules, and activity-event hooks.

**Acceptance criteria:** Owners can complete every core workflow; confirmations protect destructive actions; stale writes return conflicts; cross-account operations fail; Trash follows the 30-day rule.

**Verification:** Unit, API integration, transactional, time-controlled, account-isolation, accessibility, and browser tests.

**Risks and external prerequisites:** Product decision for deleting a list containing tasks and final activity-retention policy.

## Phase 5 Dashboard search calendar tags and reports

**Requirements addressed:** FR8-FR10, FR14-FR16, FR19, NFR4, NFR7, NFR9, O3 foundations.

**Dependencies:** Stable task model, timezone utilities, query and pagination conventions.

**Deliverables:** Dashboard, combined search filters, sorting, pagination, monthly and weekly calendar, small-screen agenda view, tags, bulk actions, and productivity reports.

**Acceptance criteria:** Fixed data produces exact expected counts and date categories; combined filters and sorting are deterministic; bulk actions are atomic; supported viewport and browser checks pass.

**Verification:** Fixed-dataset tests, query integration tests, visual viewport matrix, accessibility checks, and Chrome/Firefox browser tests.

**Risks and external prerequisites:** Calendar complexity, daylight-saving boundaries, representative datasets, and browser test capacity.

## Phase 6 Recurrence reminders history and data portability

**Requirements addressed:** FR12, FR13, FR17, FR18, remaining FR20, NFR11, NFR15.

**Dependencies:** Worker and broker, outbox/idempotency model, email adapter, stable task services.

**Deliverables:** Recurring definitions and generation, reminders, in-app notifications, optional email, history UI, versioned export, validated preview, transactional import, account deletion.

**Acceptance criteria:** Worker restarts and retries do not duplicate tasks or notifications; fixed recurrence and reminder datasets match expected results; invalid imports make no changes; exports and history remain account-isolated.

**Verification:** Clock-controlled tests, worker restart tests, retry and deduplication tests, import rollback tests, security tests, and browser acceptance.

**Risks and external prerequisites:** Broker operations, email limits, task scheduling semantics, export storage, and retention decisions.

## Phase 7 Verification and user acceptance

**Requirements addressed:** O1-O4, NFR4-NFR9, NFR11, NFR15.

**Dependencies:** Feature-complete release candidate and stable test environment.

**Deliverables:** Acceptance index, volunteer usability protocol, fixed dataset, accessibility review, cross-browser record, security and integrity suites, and performance workload.

**Acceptance criteria:** At least one acceptance test passes per FR; at least four of five volunteers complete the defined workflow within five minutes without help; fixed dataset has complete agreement; NFR5 percentile target and O4 suites pass.

**Verification:** Recorded automated runs and dated manual evidence.

**Risks and external prerequisites:** Five independent volunteers, representative hardware, stable Chrome and Firefox versions, and time for remediation. Results must not be fabricated.

## Phase 8 Production deployment and handoff

**Requirements addressed:** NFR3, NFR10, NFR12-NFR14, O5.

**Dependencies:** Verified release candidate, hosting choice, credentials, backup destination, and second developer.

**Deliverables:** Production Compose or equivalent deployment configuration, HTTPS reverse proxy, alerts, runbooks, migration and rollback procedure, backup and restore procedure, staging deployment, and handoff checklist.

**Acceptance criteria:** A second developer completes fresh setup; staging deploys; upgrade and rollback are rehearsed; isolated restore meets the documented targets or records corrective actions; alerts and health checks are demonstrated.

**Verification:** Dated rehearsal logs, screenshots where useful, command records, restored-data checks, and second-developer signoff.

**Risks and external prerequisites:** Hosting budget, DNS and TLS, provider access, backup isolation, and second-developer availability.

## Cross-phase controls

- Update traceability and progress after every phase.
- Do not mark tests, benchmarks, deployments, user studies, or restores complete without evidence.
- Review ownership enforcement whenever a new account-owned resource is added.
- Keep migrations and application changes compatible through the documented deployment sequence.
- Keep production code out of tests and documentation directories and avoid duplicate source trees.
