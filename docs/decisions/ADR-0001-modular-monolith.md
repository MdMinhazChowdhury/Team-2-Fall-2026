# ADR 0001 Use a Modular Monolith

- **Status:** Proposed
- **Date:** 2026-10-18

## Context

TaskTrack has a broad feature set but a small student team. It needs clear boundaries for authentication, tasks, scheduling, reporting, imports, and operations without the deployment and consistency burden of independently deployed services.

## Decision

Use one FastAPI backend codebase organized into modules, one React frontend, one background worker using the backend's domain services, one PostgreSQL database, and one Redis broker. Deploy them as separate processes behind one same-origin reverse proxy while treating them as one application.

## Consequences

The team gains simple local setup, transactions across related features, consistent ownership enforcement, and lower operational overhead. Modules must be kept explicit to avoid a tightly coupled codebase. Independent service scaling is deferred until measured need exists.
