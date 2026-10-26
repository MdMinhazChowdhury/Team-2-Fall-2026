# Sprint 1 task core alignment

## What I changed

I adapted my earlier task-creation and filtering work to the existing React/TypeScript/FastAPI/PostgreSQL application. I used its current models, routes, authentication, transactions, and migrations. I did not add Dennis's separate Java account code or duplicate the existing web app. The earlier Java/JUnit/SQLite files and their 20/58-test reports describe separate versions and are not evidence for this implementation.

My changes are TaskFactory, TaskFilter, their service/worker/route connections, new unit and PostgreSQL regression tests, and these alignment notes. The existing task models, GUI, authentication, imports, schedules, migrations, and broad application tests were already present. I do not claim those pre-existing features as my new implementation.

## Matching the existing design

| Earlier task core | Current application contract | Integration |
| --- | --- | --- |
| Project | TaskList; UUID ID and authenticated account_id | Existing /api/lists CRUD and version checks |
| Task | SQLAlchemy Task and validated TaskInput/TaskUpdate | Existing fields and response payloads retained |
| TaskFactory | factories.TaskFactory.create and recurring | API/import creation uses save_task; recurring worker uses recurring |
| TaskService | Existing services.save_task, owned, version, event, trash | Ownership and transactions remain outside the unsaved-object factory |
| TaskFilter | filters.TaskFilter.query | Existing /api/tasks query, pagination, search, tags, timezone categories |
| NOT_STARTED | TODO, displayed as To Do | Matches UI/schema/database; old enum is intentionally rejected |
| Immediate task deletion | Confirmed 30-day Trash, restoration, permanent deletion | Existing lifecycle retained |
| Delete a project and its tasks | Delete an empty list only, including Trash | Existing conflict response retained; no silent cascade change |
| SQLite / integer IDs | PostgreSQL / UUID IDs | No second database or language bridge introduced |

The task factory returns a new validated Task with its UUID, defaults, version, and timestamps. It has no database access and makes no commit. The service checks list/tag ownership before factory invocation; database constraints and request transactions remain authoritative. The recurring policy preserves its deduplication key, resets completion state, and uses the same creation policy. Override create for an approved future category; priorities remain data instead of artificial subclasses.

## Assignment rubric mapping

Source: the supplied CMSC 430 Phase 2 Sprint 1 Assignment. The goal is functional logic plus an initial GUI. I am Person C; Dennis is Person B; James is Person D. The B/C report requirement covers implementation, Factory Pattern, test cases/results, and communication. Integration tests are explicitly required in the instructions even though they have no separate B/C score line.

| Requirement | Source or evidence | Status |
| --- | --- | --- |
| Key classes, fields, methods matching the design | Existing models/schemas/services plus factories.py and filters.py | Aligned with the current web design; earlier Java UML must be updated by the team |
| Factory Pattern and extensibility | TaskFactory.create/recurring; injected service factory; tests/unit/test_task_core.py | Implemented; API/import/recurrence paths tested |
| Unit tests in isolation with stubs | tests/unit/test_task_core.py, SessionStub, RecordingFactory | Includes successful, invalid, and boundary inputs; no database required |
| Integration tests of real modules | tests/backend/test_person_c_core.py and inherited backend suite | Real PostgreSQL, API, authentication, validation, search, status, Trash, import, recurrence |
| /src, /tests, /docs structure | Existing source layout and new tests/unit, docs/person-c | Preserved |
| GUI integration evidence | Existing React client contract and frontend/browser suites | API shapes unchanged; local verification recorded separately |
| Communication log with three different days and attachments | Student's original communications | Not generated or verified by code tests; original dated evidence is still required |
| Submission to D2L | Student report and evidence | Not performed by these code changes |

The sprint assignment does not itself mandate Java. The prior proposal/UML used Java/JavaFX/SQLite, while the current team code and repository plan use a web stack. This update follows the requested current repository, but it does not establish instructor approval of that design change. The web scope has no Administrator model; the old administrator use cases are not silently represented as implemented. The team must reconcile those design documents rather than maintain incompatible systems.

## Product requirements and plan coverage

| Requirement area | Current source | Tests |
| --- | --- | --- |
| FR2 list CRUD | task_api lists/create_list/rename_list/delete_list, TaskList | Existing list-validation/confirmation/version tests |
| FR3–FR7 tasks, edit/status/priority/Trash | schemas, TaskFactory, save_task, task_api | Factory unit cases; API lifecycle/validation/conflict/Trash tests |
| FR8–FR10 dashboard, combined filtering/sorting/pagination | TaskFilter and existing task_api | Inclusive date range, null deadlines, literal search wildcards, tags, boundaries, existing workload |
| FR11–FR13 checklists/recurrence/reminders | Existing services/jobs plus factory recurrence | Existing checklist/reminder/deduplication tests and new factory regression |
| FR14–FR20 calendar/tags/bulk/history/import/export/reports/settings | Existing extras_api, jobs, services, frontend | Inherited suites retained; import creation now explicitly checks factory use |
| NFR2/NFR6/NFR8 ownership, data integrity, validation | Existing owned checks, PostgreSQL constraints, transactions, errors | Existing isolation/stale-write/rollback tests and new core cases |
| NFR5 performance | Existing 10-account, 500-tasks/account workload | Fresh measurements saved in this update's evidence, with TestClient transport limits |
| NFR10/NFR14 structure and checks | Existing dependency locks/CI; unit suite included; .gitattributes | New isolated and full runs; lint/types/build/format checks |

The larger final-release plan also requires Firefox, container/Redis/Celery restart verification, live email, production HTTPS/alerts, restore/deployment rehearsals, volunteer usability, and independent signoff. Those are not certified by this task-core update. Existing docs/verification.md retains the detailed FR1–FR20/NFR/objective mapping and limitations; no requirement is silently removed.

## Reproduce

Install the locked Python/npm dependencies following the root README. For tests without PostgreSQL:

```powershell
.\.venv\Scripts\python.exe -m pytest --confcutdir=tests/unit tests/unit
```

For the complete suite, configure TASKTRACK_TEST_DATABASE_URL to a disposable PostgreSQL database and run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit tests/backend tests/performance
.\.venv\Scripts\python.exe -m ruff check src/backend tests
.\.venv\Scripts\python.exe -m ruff format --check src/backend tests
.\.venv\Scripts\python.exe -m mypy
npm.cmd run lint
npm.cmd run format:check
npm.cmd run build
npm.cmd test
```

The existing fixture creates and drops only randomly named schemas in that explicitly selected test database. No fallback SQLite results are used. Recorded evidence for this update is kept under this folder rather than overwriting the earlier Person D results.


## Observed results for this update

I ran the final local checks on October 25, 2026 using Python 3.12.14, Node 24.22.1, and an isolated PostgreSQL 18.6 server bound to loopback. The implementation declares Python >=3.12; these differ from the earlier contributor's recorded Python/Node versions and are recorded separately.

- Full unit/backend/performance suite: **65 passed** (23 isolated core cases, 9 new PostgreSQL regression cases, 33 pre-existing backend/performance cases), zero failures/skips, 19.93 seconds.
- Unit-only run without PostgreSQL: **23 passed**, 1.34 seconds.
- Existing frontend suite: **8 passed**.
- Installed Chrome browser suite: **3 passed**, 18.1 seconds. It exercises registration/verification, list/task lifecycle, persistence through reload, filters, confirmation/Trash/restore, responsive widths, automated accessibility, and organization/import/export.
- Python lint/format/types and frontend lint/format/production build: **passed**.
- Existing performance workload: 10 concurrent accounts with 500 tasks each; 100 retrieval/update requests; measured p95 **0.249 seconds**, below the 2-second target. This is in-process ASGI plus real PostgreSQL, excluding external network/proxy latency.

Evidence: [backend results](evidence/backend-results.xml), [backend console](evidence/backend-console.txt), [Chrome browser console](evidence/browser-console.txt), [frontend console](evidence/frontend-console.txt), [build output](evidence/build-console.txt), [performance](evidence/performance.json), [quality checks](evidence/quality-checks.txt), and [screenshots](evidence/screenshots/). The earlier contributor's evidence files were restored unchanged after the tests generated their outputs.

The original Java-only branch remains separate. This local update starts from the current team web implementation and adds only the task-core alignment described above. The current Word reports and older ZIPs describe earlier Java versions; they must not be submitted as proof of this web implementation without revision. Communication dates/attachments, team acceptance of the design change, and the remaining release gates are still outside these automated test results.
