# Sprint 2 Task Backend Handoff

Elijah Navarro | Person C | November 14, 2026

## Backend change

The task listing and export paths formerly fetched checklist items and tags once per task. The updated service fetches both collections in two account-scoped queries and groups them by task ID before serializing the response. For a page of 25 tasks, the child-query count drops from 50 (derived from the Sprint 1 source) to 2 (measured by the PostgreSQL integration test).

The existing GET /api/tasks response, filters, pagination, and checklist ordering still apply. Single-task reads and export use the same serializer. The model and database schema are unchanged. For the architecture diagram, show the task API and export service calling the shared task-detail service, which reads Task, ChecklistItem, and TaskTag data through SQLAlchemy.

## Defect status entries for the shared table

| Item | Status | Verification |
| --- | --- | --- |
| Per-task checklist and tag queries on task listing and export | Fixed locally | 25-task API test verifies two child queries and exact checklist/tag contents per task. The existing export and import tests passed. |
| Team's other Sprint 1 defects | Awaiting shared list | Add confirmed defects with owners and final status. This document records the task backend changes only. |

## Test evidence for Ian

| Check | Expected | Actual |
| --- | --- | --- |
| Task listing with 25 records and mixed checklist/tag data | Two child reads. Each task keeps its own ordered checklist and tags. | Passed |
| Sprint 1 Python regression plus new case | Unit, API, authorization, database CRUD, migrations, and workload tests pass. | 83 passed, 0 failures, 0 skips |
| Workload with 10 concurrent accounts and 500 tasks per account | Retrieval and update p95 below 2 seconds. | 183 ms p95 over 100 requests. See evidence/task-performance.json. |
| Authorization and security regression | Existing account isolation, administrator restrictions, session revocation and error-redaction cases pass. | Passed within the Python suite |
| Frontend unit regression | Existing component and date tests pass. | 8 passed |

The workload used a local PostgreSQL 18.6 database and an in-process ASGI client on Windows. It excludes browser, network and reverse-proxy latency. Reproduce with the repository's disposable PostgreSQL setup and run pytest tests/unit tests/backend tests/performance. Python lint, mypy, frontend type checking, and the frontend production build passed. No new browser or full GUI integration result is recorded here.

The team still needs to reconcile the shared Sprint 1 defect list and run coordinated GUI regression. Add genuine Sprint 2 contact dates and original evidence to the submission separately.
