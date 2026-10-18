# TaskTrack Data Model Outline

## Modeling conventions

- Primary keys use UUIDs.
- Account-owned records include `account_id` directly when practical.
- Event timestamps are timezone-aware UTC values.
- Calendar-only due dates use a date type.
- Mutable aggregate roots include a version integer for optimistic concurrency.
- Created and updated timestamps are maintained consistently.
- Sensitive tokens are represented only by hashes and expiry metadata.

## Core entities

### Account

Fields: id, email, normalized_email, password_hash, email_verified_at, timezone, notification_preferences, status, created_at, updated_at, deleted_at.

Constraints: unique normalized_email; valid IANA timezone; deletion status controls access.

### Session

Fields: id, account_id, secret_hash, created_at, last_seen_at, expires_at, revoked_at, user_agent_summary, network_metadata.

Constraints: secret_hash unique; account-scoped indexes for active-session listing and revocation.

### VerificationToken and RecoveryToken

Fields: id, account_id, token_hash, purpose, created_at, expires_at, consumed_at.

Constraints: token_hash unique; single use; purpose and expiry checked transactionally.

### TaskList

Fields: id, account_id, name, position, version, created_at, updated_at.

Constraints: normalized name unique per account if product validation adopts that rule; ownership required for every operation.

### Task

Fields: id, account_id, list_id, title, description, due_date, status, priority, version, recurrence_rule_id, recurrence_occurrence_key, completed_at, deleted_at, purge_after, created_at, updated_at.

Constraints: title required; status in To Do, In Progress, Completed; priority in Low, Medium, High with Medium default; list and account must agree; unique recurrence occurrence key when present.

### ChecklistItem

Fields: id, account_id, task_id, text, position, is_completed, completed_at, created_at, updated_at.

Constraints: task and account must agree; position ordered within a task.

### Tag and TaskTag

Tag fields: id, account_id, name, normalized_name, created_at, updated_at.

TaskTag fields: account_id, task_id, tag_id, created_at.

Constraints: tag name unique per account; composite uniqueness prevents duplicate assignment; all linked records share an owner.

### RecurrenceRule

Fields: id, account_id, source_task_id, frequency, interval, local_start, account_timezone, optional_end_date, next_occurrence_at, active, created_at, updated_at.

Constraints: supported frequencies are daily, weekly, and monthly; occurrence generation uses a deterministic key.

### Reminder

Fields: id, account_id, task_id, channel, local_schedule, scheduled_for_utc, status, delivery_key, attempt_count, last_error_code, delivered_at, created_at, updated_at.

Constraints: delivery_key unique; email reminders require account opt-in and verified email.

### Notification

Fields: id, account_id, task_id, reminder_id, type, title, body, read_at, created_at.

Constraints: notification creation is idempotent for one delivery key.

### ActivityEvent

Fields: id, account_id, task_id, actor_account_id, event_type, changed_fields, occurred_at.

Constraints: append-only from business services; payload excludes secrets and avoids unnecessary private snapshots.

### ImportBatch

Fields: id, account_id, format_version, source_hash, status, record_counts, validation_summary, preview_expires_at, applied_at, created_at.

Constraints: account-scoped; full validation precedes one-transaction application; source_hash may support duplicate detection.

### ExportJob

Fields: id, account_id, format_version, status, requested_at, completed_at, expires_at, storage_reference, error_code.

Constraints: storage references are account-scoped and expire; exported content is not exposed by predictable identifiers.

### JobExecution and OutboxEvent

JobExecution fields: id, job_type, idempotency_key, status, attempt_count, scheduled_at, started_at, completed_at, last_error_code.

OutboxEvent fields: id, aggregate_type, aggregate_id, event_type, payload, created_at, published_at.

Constraints: idempotency_key unique; outbox writes share the business transaction that creates work.

## Important relationships

- Account owns sessions, lists, tasks, tags, reminders, notifications, activity, imports, and exports.
- TaskList contains tasks.
- Task contains checklist items and may reference one recurrence rule.
- Tasks and tags have a many-to-many relationship through TaskTag.
- Task may have multiple reminders and activity events.
- RecurrenceRule generates tasks with unique occurrence keys.
- Reminder produces at most one in-app notification per delivery key.

## Deletion behavior

Account deletion is a controlled workflow that revokes sessions, blocks new access, and removes or anonymizes account data according to the approved retention policy. List deletion requires confirmation and a documented decision on whether contained tasks move to Trash or block deletion. Task deletion uses the 30-day Trash lifecycle.

## Migration sequence

1. Accounts, sessions, and tokens.
2. Lists, tasks, and checklist items.
3. Tags and task-tag associations.
4. Recurrence, reminders, and notifications.
5. Activity history.
6. Imports, exports, job execution, and outbox records.
7. Performance indexes and constraints verified with representative data.

The exact physical schema and indexes will be finalized in Phase 2 before the first Alembic migration.
