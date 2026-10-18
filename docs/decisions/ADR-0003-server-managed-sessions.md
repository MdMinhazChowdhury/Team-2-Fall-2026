# ADR 0003 Use Server Managed Sessions

- **Status:** Proposed
- **Date:** 2026-10-18

## Context

TaskTrack is a same-origin browser application containing private user data. It needs logout, session listing, revocation, password-change invalidation, and secure account deletion.

## Decision

Use opaque session identifiers in Secure, HttpOnly, SameSite cookies. Store only a hash of each session secret with account, expiry, revocation, and limited device metadata. Require CSRF protection for state-changing requests and rotate sessions after authentication-sensitive events.

## Consequences

The server can revoke sessions reliably and browser scripts cannot read the secret. The application must manage session cleanup and CSRF tokens. Horizontal deployment requires shared PostgreSQL session state, which is already part of the architecture.
