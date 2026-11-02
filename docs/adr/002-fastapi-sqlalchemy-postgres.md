# ADR-002: FastAPI + SQLAlchemy 2 + Alembic on PostgreSQL (also in tests)

- **Status:** Accepted
- **Date:** 2026-11-02

## Context
The PRD asks for a FastAPI backend and PostgreSQL, with "SQLite locally". The backend needs typed request validation, generated OpenAPI documentation, async support for provider calls, and versioned schema migrations.

## Decision
- FastAPI with Pydantic v2 for routing, validation and OpenAPI.
- SQLAlchemy 2.0 (typed `Mapped[]` models) with Alembic migrations.
- **PostgreSQL 16 everywhere: local (Docker Compose), CI and production.** This replaces the PRD's "SQLite locally".

## Alternatives considered
- **SQLite for local development and tests:** zero setup, but trigram indexes, `ILIKE`, `jsonb`, `citext`, enum types, and unique-violation behaviour under concurrency all differ. The idempotency race test would pass on SQLite and say nothing about production.
- **SQLModel:** less boilerplate, but it lags SQLAlchemy 2 features and mixes API schemas with persistence models.
- **Raw SQL / asyncpg:** fastest, but no migrations or model layer for little gain at this scale.

## Consequences
- Docker becomes the one local prerequisite. `docker compose up db` is enough for running tests.
- The tests exercise the real database behaviour that the design depends on.
