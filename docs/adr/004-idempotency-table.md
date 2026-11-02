# ADR-004: Idempotency keys stored in a Postgres table

- **Status:** Accepted
- **Date:** 2026-11-02

## Context
Re-running a check calls an external provider, which may be billed per call and has side effects. A double click, two tabs, or a client network retry must never cause two provider calls (PRD S1).

## Decision
- The client sends `Idempotency-Key: <uuid>`. The server keeps the `idempotency_keys(key, actor_id)` primary key with `request_hash`, `response_status`, `response` and `created_at`.
- The key row is **inserted and committed before** the provider call. A concurrent duplicate hits the primary key and either replays the stored response, gets `409 request_in_progress`, or gets `422 idempotency_key_reused`.
- The check update, the stage update, the audit entry, and the stored response are written in one transaction. Keys expire after 24 h.

## Alternatives considered
- **Redis `SET NX` with a TTL:** the standard choice at scale, but it is another piece of infrastructure, and the guard would not be in the same transaction as the check update.
- **Row lock on the check (`SELECT … FOR UPDATE`):** serialises concurrent retries but cannot replay the first response, so the client cannot tell "already done" from "done now".
- **Frontend debouncing only:** does not protect against two tabs, client retries, or API clients.

## Consequences
- Correct under concurrency, uses the existing database, and is testable in pytest.
- One extra write per retry, which is negligible at this volume.
