# TaskTrack Requirements

## Project identity

### Project name

TaskTrack Task Management Application

### Project description

For our project, we want to develop a web-based task management application that helps students and individual users organize their responsibilities in one place. Users will be able to create an account, organize tasks into lists, set deadlines and priorities, and track their progress. The application will also support subtasks, recurring tasks, reminders, and a calendar view so users can manage both larger assignments and everyday responsibilities. Search, filters, tags, and bulk actions will help users find and update their work efficiently. A dashboard will summarize upcoming, overdue, and completed tasks, while activity history and productivity reports will help users review their progress. Deleted tasks will remain recoverable for a limited time, and users will be able to export and import their task data. Each account will manage its own private information. Our goal is to build a practical application with a usable interface, secure account access, reliable database storage, and testing that demonstrates the system works as intended.

## Functional requirements

- **FR1.** Users shall be able to register, verify their email address, log in, log out, and securely reset a forgotten password.
- **FR2.** Users shall be able to create, rename, view, and delete their own task lists. List deletion shall require confirmation.
- **FR3.** Users shall be able to create tasks with a required title and optional description and due date, organized within one of their lists.
- **FR4.** Users shall be able to view and edit task details and move tasks between their own lists.
- **FR5.** Users shall be able to delete tasks after confirmation, restore them from Trash within 30 days, or permanently delete them.
- **FR6.** Users shall be able to change task status between To Do, In Progress, and Completed and reopen completed tasks.
- **FR7.** Users shall be able to assign Low, Medium, or High priority, with Medium as the default.
- **FR8.** The dashboard shall show incomplete tasks due today, upcoming tasks, overdue tasks, and counts by status.
- **FR9.** Users shall be able to search task titles and combine filters for list, status, priority, tag, and due-date category.
- **FR10.** Users shall be able to sort tasks by due date, priority, or creation date and navigate paginated results.
- **FR11.** Users shall be able to create, edit, reorder, complete, and delete checklist items within a task.
- **FR12.** Users shall be able to configure recurring tasks using daily, weekly, and monthly schedules, with an optional end date.
- **FR13.** Users shall be able to configure task reminders, receive in-app notifications, and optionally receive email reminders.
- **FR14.** Users shall be able to view dated tasks in monthly and weekly calendar views and open task details from the calendar.
- **FR15.** Users shall be able to create, rename, delete, and assign personal tags to tasks.
- **FR16.** Users shall be able to select multiple tasks and complete, move, reprioritize, or move them to Trash in one operation.
- **FR17.** Users shall be able to view a task's activity history, including creation, relevant edits, completion, reopening, and restoration.
- **FR18.** Users shall be able to export task data and import a supported TaskTrack export file after validation and a preview.
- **FR19.** Users shall be able to view personal productivity reports showing task completions over a selected date range and current task counts by status.
- **FR20.** Users shall be able to manage their timezone and notification preferences, change their password, revoke sessions, and delete their account.

## Optional features and nonfunctional requirements

The assignment labels this section "Optional features," but explicitly asks for nonfunctional requirements. The following are quality constraints, security controls, and operational requirements rather than optional user-facing features.

- **NFR1.** Passwords shall be stored using a maintained Argon2id implementation, and recovery, verification, and session secrets shall not be stored in plaintext.
- **NFR2.** Every operation shall enforce account ownership on the server, preventing access to another user's lists, tasks, tags, notifications, exports, and activity records.
- **NFR3.** Production traffic shall use HTTPS, secure session cookies, CSRF protection, and appropriate security headers.
- **NFR4.** The main interface shall remain usable from 360 to 1920 pixels wide without horizontal page scrolling. Calendar layouts shall provide an appropriate small-screen presentation.
- **NFR5.** Under a documented test with 10 simultaneous authenticated users and at least 500 tasks per account, 95% of task retrieval and update requests shall complete within two seconds.
- **NFR6.** Confirmed task changes shall persist through logout and normal application or worker restarts. Multi-record changes shall maintain transactional integrity.
- **NFR7.** Core workflows shall target WCAG 2.2 AA through accessible controls, keyboard support, visible focus, appropriate contrast, and labels, verified through automated and manual checks.
- **NFR8.** The server shall validate inputs and return useful errors without exposing secrets, internal exceptions, or database details.
- **NFR9.** Core workflows shall pass acceptance tests in the stable versions of Chrome and Firefox recorded at release testing.
- **NFR10.** The repository shall separate source code, tests, and documentation using the required structure and provide versioned migrations, locked dependencies, and setup instructions verified by a second developer.
- **NFR11.** Scheduled work shall survive worker restarts and use retry and deduplication mechanisms that prevent duplicate recurring task instances and duplicate in-app reminders.
- **NFR12.** Database recovery shall target a recovery point within 24 hours and service restoration within four hours, with an isolated restore exercise documenting actual results.
- **NFR13.** Production operation shall include structured logs, request identifiers, health checks, and configurable alerts for service failures, failed backups, and persistent job failures.
- **NFR14.** Continuous integration shall check formatting, linting, types, tests, builds, and applicable security scans before a release is approved.
- **NFR15.** Import operations shall enforce file and record limits, validate the entire input, and avoid partially applying an import when validation or persistence fails.

## Exactly five measurable objectives

1. **O1.** By the final demonstration, implement all approved functional requirements and pass at least one acceptance test for each requirement.
2. **O2.** Have at least four of five volunteer testers create a list, create a dated task with a checklist, edit it, and complete it within five minutes after login without assistance; record findings and resulting improvements.
3. **O3.** Achieve complete agreement with expected results for a fixed dataset covering dashboard counts, date categories, recurring task generation, reminder eligibility, and productivity reports.
4. **O4.** Pass the account-isolation, session, CSRF, persistence, import-integrity, and concurrency test suites, and meet the documented performance target in NFR5.
5. **O5.** Have a second developer run the application from a fresh checkout and complete a documented staging deployment, upgrade, rollback rehearsal, and isolated backup restoration before handoff.

## Scope rules

All approved requirements remain traceable. A release sequence may defer a requirement to a later increment when team capacity requires it, but the requirement may not be silently removed or reported as complete without evidence. User testing, benchmarks, deployments, and restore exercises must be recorded only after they occur.
