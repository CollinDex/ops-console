# ADR-005: In-process asyncio pinger and a single API instance

- **Status:** Accepted
- **Date:** 2026-11-02

## Context
Provider health must be sampled every 15 s and stored for the status panel, uptime, and incident history. Hosting is a free tier with one instance.

## Decision
- An asyncio task started in the FastAPI lifespan pings the 4 providers concurrently every 15 s and writes to `provider_pings`.
- The simulated provider mode (up, slow or down) is held in process memory.
- The API runs **one uvicorn worker** and one instance.

## Alternatives considered
- **Separate worker (Celery/RQ, or an arq job), or a cron job:** correct for multiple instances, but needs a broker and a second deployable.
- **Postgres advisory lock to elect one pinger across workers:** a good middle step, but provider mode would still need to move to the database. Deferred.
- **Ping on demand when the status endpoint is called:** no history, so no uptime or incidents, and it slows the request.

## Consequences
- No extra infrastructure, and replacing simulated providers with real adapters only touches `providers/`.
- Scaling out would duplicate pings and split the simulate state. Revisit with an advisory lock plus a `provider_settings` table, or a dedicated worker, before running more than one instance.
