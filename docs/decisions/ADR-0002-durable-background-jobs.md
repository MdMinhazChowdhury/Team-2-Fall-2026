# ADR 0002 Use Celery with PostgreSQL Idempotency Records

- **Status:** Proposed
- **Date:** 2026-10-18

## Context

Recurring tasks, reminders, email attempts, exports, and cleanup must survive worker restarts, retry safely, and avoid duplicate user-visible results. Running schedules only inside the web process would lose or duplicate work during restarts and multiple-instance deployment.

## Decision

Use Celery workers with Redis as the broker. Store business schedules, outbox events, delivery state, idempotency keys, and results that affect correctness in PostgreSQL. Publish work from committed outbox records. Make recurring occurrence keys and reminder delivery keys unique. Configure bounded retries and inspectable terminal failure states.

## Alternatives considered

- In-process scheduling: rejected because restart and multi-instance behavior are unsafe for the stated requirements.
- Database polling without a queue: viable for a smaller scope, but the team would need to build retry, claiming, scheduling, and operational behavior.
- Microservices: rejected because they add deployment and consistency complexity without demonstrated need.

## Consequences

Redis becomes an additional runtime dependency justified by durable background work. PostgreSQL remains the source of truth. Workers must be designed for at-least-once delivery, and tests must prove retry and deduplication behavior. Exact supported versions will be verified in Phase 2.
