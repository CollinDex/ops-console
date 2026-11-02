# ADR-001: Monorepo with `api/` and `web/`

- **Status:** Accepted
- **Date:** 2026-11-02

## Context
The console has one FastAPI service and one Next.js app, built and reviewed together by one person on a three-day deadline. Reviewers need one link and one command.

## Decision
A single Git repository with `api/`, `web/`, `docs/`, a root `docker-compose.yml`, a `Makefile`, and one CI workflow with a separate job per app.

## Alternatives considered
- **Two repositories:** a cleaner separation of ownership, but two links, two CI setups, and the API contract and the UI could change out of step.
- **Turborepo or Nx workspace:** built for many JS packages; adds tooling with no benefit when one side is Python.

## Consequences
- An API change and the UI change that uses it can land in one commit, and generated API types stay in step with the backend.
- CI path filters keep each job focused. If the apps get separate teams later, `git subtree split` can separate them.
