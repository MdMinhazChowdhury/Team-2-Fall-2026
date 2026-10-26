# TaskTrack Traceability Matrix

## Functional requirements

| ID | Planned phase | Primary components | Verification |
|---|---:|---|---|
| FR1 | 3 | Account UI, auth API, sessions, tokens, email adapter | Unit, integration, browser acceptance, security tests |
| FR2 | 4 | List UI and list service | Unit, API integration, confirmation-flow acceptance |
| FR3 | 4 | Task editor and task service | Unit, API integration, browser acceptance |
| FR4 | 4 | Task details, move operation, concurrency | Integration and conflict tests |
| FR5 | 4 | Trash UI, soft deletion, purge job | Time-controlled integration and acceptance tests |
| FR6 | 4 | Status transitions and activity | Unit and acceptance tests |
| FR7 | 4 | Priority validation and defaults | Unit and API tests |
| FR8 | 5 | Dashboard queries and cards | Fixed-dataset agreement tests |
| FR9 | 5 | Search API and filter UI | Query integration and browser tests |
| FR10 | 5 | Sorting and pagination | Boundary, ordering, and browser tests |
| FR11 | 4 | Checklist UI and service | Unit, reorder, and acceptance tests |
| FR12 | 6 | Recurrence service and worker | Clock-controlled generation and uniqueness tests |
| FR13 | 6 | Reminder service, worker, notifications, email adapter | Eligibility, retry, deduplication, and acceptance tests |
| FR14 | 5 | Calendar API and responsive views | Date, timezone, responsive, and browser tests |
| FR15 | 5 | Tag UI and service | Unit, isolation, and acceptance tests |
| FR16 | 5 | Selection UI and transactional bulk service | Atomicity, authorization, and browser tests |
| FR17 | 6 | Activity writer and history UI | Event-content and acceptance tests |
| FR18 | 6 | Export and transactional import | Validation, preview, rollback, isolation, and acceptance tests |
| FR19 | 5 | Reporting queries and UI | Fixed-dataset agreement and browser tests |
| FR20 | 3 and 6 | Settings, sessions, account lifecycle | Security, integration, and acceptance tests |

## Nonfunctional requirements

| ID | Planned phase | Evidence |
|---|---:|---|
| NFR1 | 3 | Password and secret-hashing tests; dependency record |
| NFR2 | 3-6 | Cross-account negative test suite |
| NFR3 | 3 and 8 | Cookie, CSRF, HTTPS, and header checks |
| NFR4 | 5 and 7 | Responsive viewport matrix from 360 to 1920 pixels |
| NFR5 | 7 | Versioned workload and percentile report |
| NFR6 | 2-7 | Transaction tests and restart persistence checks |
| NFR7 | 4-7 | Automated accessibility results plus manual checklist |
| NFR8 | 2-7 | Validation and error-redaction tests |
| NFR9 | 7 | Recorded Chrome and Firefox acceptance runs |
| NFR10 | 1, 2, and 8 | Structure, migrations, lockfiles, setup verification |
| NFR11 | 6 and 7 | Worker restart, retry, and deduplication tests |
| NFR12 | 8 | Backup policy and isolated restore report |
| NFR13 | 2 and 8 | Structured-log, request-ID, health, and alert checks |
| NFR14 | 2 and 8 | Required GitHub Actions checks |
| NFR15 | 6 and 7 | Import limits, complete validation, and rollback tests |

## Objectives

| ID | Supporting requirements | Required evidence |
|---|---|---|
| O1 | FR1-FR20 | At least one passing acceptance test per approved FR |
| O2 | FR2, FR3, FR4, FR11, NFR4, NFR7 | Four of five successful timed volunteer sessions plus findings and changes |
| O3 | FR8, FR12, FR13, FR19 | Fixed dataset, expected outputs, and complete agreement report |
| O4 | NFR1-NFR6, NFR8, NFR11, NFR15 | Passing security, persistence, integrity, concurrency, and performance suites |
| O5 | NFR10, NFR12-NFR14 | Fresh-checkout setup, staging deployment, upgrade, rollback, and restore record |

## Evidence policy

A requirement or objective remains Planned until linked evidence exists. The team will not substitute screenshots for automated test evidence where the requirement concerns correctness, security, transactions, or performance. User tests, benchmarks, deployments, and restore exercises must be dated and reproducible.

## Current implementation evidence

The planning matrix above is retained. Current source/test mappings, measured results and remaining qualifications are maintained in [verification.md](verification.md) and [progress.md](progress.md). No release objective is marked complete solely because implementation files now exist.

The factory and filtering alignment for FR3/FR4/FR6/FR7/FR9/FR10/FR12/FR18, together with the Sprint 1 Person C rubric, is mapped in [person-c/ALIGNMENT.md](person-c/ALIGNMENT.md). Existing requirement IDs and API behavior are preserved.
