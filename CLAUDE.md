# CrediSure Ops Console

An internal ops dashboard for the CrediSure engineering assessment. The stack is Next.js 15 + TypeScript + Tailwind + shadcn/ui (`web/`), FastAPI + SQLAlchemy 2 + Alembic (`api/`), and PostgreSQL 16. All data is seeded and fictional.

## Source of truth
- `docs/system-design.md` is the approved design: contracts, data model, error codes and flows. **Don't change it during implementation.** If it seems wrong, record that in your phase report.
- `docs/adr/` holds the decisions and why they were made.
- `docs/build/README.md` describes the workflow and the phase list. `docs/build/phase-N-*.md` is the spec for each phase.

## Workflow (Opus plans → Sonnet implements → Opus reviews)
- **Implementing a phase:** follow `docs/build/README.md` → "Rules for the implementer". Work on branch `phase/N-<slug>`, build only what that phase doc lists, run its **Verify** commands, write `docs/build/reports/phase-N-implementation.md` from the template, and **don't merge or push**.
- **Reviewing a phase:** follow "Rules for the reviewer". Re-run Verify, fix issues on the same branch with one commit per fix, and write `docs/build/reports/phase-N-review.md`.
- The reviewer fast-forward merges each clean phase into `main`. Nobody pushes unless the owner asks.

## Conventions
- **Commits:** one line in Conventional Commits form (`feat(api): …`, `fix(web): …`, `test(api): …`, `docs: …`, `chore: …`), short and to the point. **Never** a body, `Co-Authored-By`, or any AI attribution trailer.
- Python uses ruff (line length 100), mypy strict on `app/`, pytest against **Postgres** (`credisure_test`, never SQLite).
- Web uses ESLint, Prettier and `tsc --noEmit`. API types come from `pnpm gen:api` (`src/lib/api-types.ts` is generated; never edit it by hand).
- Every API error uses `{"error": {"code", "message", "request_id"}}` with the codes from design §6.5.
- Never store, return or log a full BVN or account number. Last-4 digits only (ADR-006).
- Status colours always come with an icon and text.

## Commands (from repo root)
`make install` · `make dev` (full stack) · `make db` · `make migrate` · `make seed` · `make lint` · `make test` · `make web-check` · `make web-test`

Local ports: web 3000, API 8000 (`/docs` for Swagger), Postgres **5433** on the host.

Demo logins: `admin@credisure.demo` / `Admin@2026`, `analyst@credisure.demo` / `Analyst@2026`, `viewer@credisure.demo` / `Viewer@2026`.
