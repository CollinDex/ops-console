# Phase 1 implementation report

- **Branch:** `phase/1-repo-setup`
- **Implementer:** Sonnet
- **Date:** 2026-11-02
- **Commits:**
```text
b510dd0 fix(web): pin pnpm version for docker build
c7cf737 feat(web): add next.js skeleton with placeholder page
7fb063d feat(api): add api skeleton with health endpoint
91e7300 ci: add github actions workflow for api and web
58cc2de chore: add docker compose stack and pre-commit config
049e8da chore: add editorconfig, readme, contributing and makefile
```
(`main` holds `e945bdf docs: add system design, ADRs and build plan`.)

## Summary
Created the monorepo skeleton: root tooling (Makefile, compose, pre-commit, CI, editorconfig), a FastAPI skeleton with a `/health` endpoint and the full design §4.1 tree, and a Next.js 15 skeleton with shadcn/ui, the §4.2 folder tree and a placeholder page that calls `/health`. Lint, test, web-check and the docker stack all run as specified.

## Acceptance criteria
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `main` has the docs commit; Phase 1 work is on the branch | ✅ | `git log` above |
| 2 | Tree matches §4.1 and §4.2; placeholders have a docstring naming their phase | ✅ | `api/app/**`, `web/src/**` (`.gitkeep` in empty web folders) |
| 3 | `make install` succeeds | ✅ | output below (run in the existing tree, not a fresh clone) |
| 4 | `make lint` passes; `make test` passes with db up | ✅ | output below |
| 5 | `make web-check` passes | ✅ | output below |
| 6 | compose starts all three; `/health` 200 ok; web shows API ok | ✅ | curl output below; page text read in browser pane showed `API: ok` |
| 7 | Stopping db gives 503 `"db":"down"` | ✅ | output below |
| 8 | No real secrets; `.env.example` files list all variables | ✅ | only dummy `dev-only-change-me` in `api/.env.docker` |
| 9 | CI YAML valid | ⚠️ | `actionlint` not installed; only checked that the YAML parses with PyYAML |

## Verify output
```text
$ make install
cd api && uv sync
Resolved 48 packages in 12ms
Audited 45 packages in 6ms
cd web && pnpm install
Lockfile is up to date, resolution step is skipped
Already up to date
uvx pre-commit install
pre-commit installed at .git/hooks/pre-commit

$ make lint
cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
All checks passed!
46 files already formatted
Success: no issues found in 40 source files
cd web && pnpm lint && pnpm format:check
> eslint
> prettier --check .
Checking formatting...
All matched files use Prettier code style!

$ make db && make test
 Container ops-console-db-1 Running
... (coverage table) ...
TOTAL                                 65     10    85%
1 passed, 1 warning in 0.12s

$ make web-check
(tsc --noEmit, then next build) ... Compiled successfully; routes: / and /_not-found, both static

$ docker compose up --build -d && sleep 15 && curl -s localhost:8000/health && curl -s -o /dev/null -w "%{http_code}\n" localhost:3000
{"status":"ok","db":"ok","version":"0.1.0","time":"2026-11-02T23:02:37.654518+00:00"}
200

$ docker compose stop db && curl -s -w " %{http_code}\n" localhost:8000/health; docker compose start db
{"status":"degraded","db":"down","version":"0.1.0","time":"2026-11-02T23:02:45.924689+00:00"} 503

$ docker compose down
(containers and network removed; volume ops-console_db-data kept)
```
The first `docker compose up --build` failed on the web image (see Deviations); the output above is from the re-run after the fix. The earlier tail of `make web-check` output was truncated in my capture, but it exited successfully (`make` printed no error).

## Files added or changed
- Root: `.gitignore` (on `main`), `.editorconfig`, `README.md`, `CONTRIBUTING.md`, `Makefile`, `docker-compose.yml`, `docker/postgres/init.sql`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`.
- `api/`: `pyproject.toml`, `uv.lock`, `.python-version`, `Dockerfile`, `.dockerignore`, `.env.example`, `.env.docker`, `alembic/` + `alembic.ini`, `app/` tree per §4.1, `scripts/` (`seed.py`, `start.sh`), `tests/`.
- `web/`: Next.js 15.5 app, shadcn components (plus `textarea` and `input-group`, pulled in as dependencies of other components), `.prettierrc.json`, `Dockerfile`, `.env.example`, folder tree per §4.2.

## Deviations / questions
- **shadcn init:** the current CLI no longer has a "slate" base-colour option (`-b` now selects the component library; presets are nova/vega/...). I ran `init -d -b radix` (style `radix-nova`), then set `baseColor` to `slate` in `components.json` and replaced the neutral oklch values in `globals.css` with the Tailwind slate palette by hand.
- **pnpm pin:** the docker web build failed because corepack pulled a newer pnpm whose `minimumReleaseAge` policy rejected the lockfile. Fixed by adding `"packageManager": "pnpm@10.25.0"` to `web/package.json` (commit `fix(web): pin pnpm version for docker build`). CI uses `pnpm/action-setup` reading this field.
- **Health body when db is down:** returns `"status":"degraded"` (the spec only fixes `"db":"down"` and 503). Exception text is logged, not returned.
- **Health route path:** mounted at `/health` (root), not `/api/v1/health`, matching the spec's curl.
- **pre-commit prettier hook:** the spec's `pnpm -C web prettier --write` failed under pre-commit (file paths are repo-relative), so the hook is `bash -c 'cd web && pnpm exec prettier ...'`. That fix landed in the web commit rather than its own.
- **pre-commit ruff rev** is pinned to `v0.8.6`, older than the locked ruff (0.17.3); I could not verify a newer tag offline. The reviewer may want to align it.
- `create-next-app` generated `eslint` script (not `next lint`) and `next dev/build --turbopack`; left as is. Next resolved to 15.5.28, React 19.1.
- Pytest shows one `StarletteDeprecationWarning` (httpx with `starlette.testclient`); harmless, left alone.
- `make install` was run in the working tree, not a fresh clone.

## Known gaps / follow-ups
- `actionlint` not run; CI has never executed.
- `api/app/db/session.py` creates the engine at import, so importing `app.main` with an unreachable DB is fine (lazy connect), but the test conftest relies on `DATABASE_URL` being set before import.
- `scripts/start.sh` has no migrate/seed yet (Phase 2).
