# Phase 1: Repository setup & tooling

| | |
|---|---|
| **Branch** | `phase/1-repo-setup` (the first commit goes on `main`, see step 1) |
| **Depends on** | nothing |
| **Read first** | design §4.1 (backend layout), §4.2 (frontend layout), §10 (testing), §11 (deployment), ADR-001, ADR-002 |
| **Estimated effort** | 1–1.5 h |

## Goal
Create an empty but fully wired monorepo. When this phase is done, `docker compose up` starts Postgres, an API that answers `/health`, and a Next.js placeholder page, and lint, test and CI all run green. **No feature code.**

## Local toolchain (already installed on the owner's machine)
Python 3.12 managed with **uv** · Node 22 with **pnpm** · Docker with Compose v2 · make · git.

## Steps

### 1. Git
- `git init -b main` at the repo root (`/Users/dex/Documents/credisure/ops-console`). `docs/` and `CLAUDE.md` already exist. Add `.gitignore` first (so `docs/_render/node_modules/` is excluded), then make the first commit on `main` with `docs/`, `CLAUDE.md` and `.gitignore` as `docs: add system design, ADRs and build plan`, then `git switch -c phase/1-repo-setup`.
- `.gitignore` covers Python (`__pycache__/`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`), Node (`node_modules/`, `.next/`, `out/`, `*.tsbuildinfo`), env files (`.env`, `.env.*` but **not** `.env.example`), OS files (`.DS_Store`), and `docs/_render/node_modules/`.
- `.editorconfig`: UTF-8, LF, final newline, 2 spaces by default, 4 for `*.py`.

### 2. Root files
```
README.md            stub: one paragraph, "Quick start: make dev", link to docs/system-design.md (Phase 7 writes the full version)
CONTRIBUTING.md      branch naming (phase/N-…, feat/…, fix/…), Conventional Commits, the build workflow (link docs/build/README.md)
Makefile             see below
docker-compose.yml   see below
.pre-commit-config.yaml
.github/workflows/ci.yml
docker/postgres/init.sql
```

**Makefile targets** (each one must work from the repo root):

| Target | Does |
|---|---|
| `make dev` | `docker compose up --build` |
| `make db` | `docker compose up -d db` |
| `make api-install` | `cd api && uv sync` |
| `make web-install` | `cd web && pnpm install` |
| `make install` | both of the above, plus `uvx pre-commit install` |
| `make lint` | `cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app`, then `cd web && pnpm lint && pnpm format:check` |
| `make fmt` | ruff format + ruff check --fix, then prettier --write |
| `make test` | `cd api && uv run pytest` (needs `make db`) |
| `make web-check` | `cd web && pnpm typecheck && pnpm build` |
| `make migrate` | `cd api && uv run alembic upgrade head` |
| `make seed` | `cd api && uv run python -m scripts.seed $(ARGS)` with `ARGS ?=` (the target exists now; the seed arrives in Phase 2) |

### 3. Docker Compose
```yaml
services:
  db:
    image: postgres:16-alpine
    environment: { POSTGRES_USER: credisure, POSTGRES_PASSWORD: credisure, POSTGRES_DB: credisure }
    ports: ["5433:5432"]          # 5433 on the host avoids clashing with other local Postgres instances
    volumes: [db-data:/var/lib/postgresql/data, ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro]
    healthcheck: { test: ["CMD-SHELL", "pg_isready -U credisure"], interval: 3s, timeout: 3s, retries: 20 }
  api:
    build: ./api
    env_file: ./api/.env.docker   # committed: non-secret local defaults only
    depends_on: { db: { condition: service_healthy } }
    ports: ["8000:8000"]
  web:
    build: { context: ./web, args: { NEXT_PUBLIC_API_URL: "http://localhost:8000" } }
    depends_on: [api]
    ports: ["3000:3000"]
volumes: { db-data: {} }
```
- `docker/postgres/init.sql` creates a second database, `credisure_test`, for pytest.
- `api/.env.docker` is committed and holds only local, non-secret values (`DATABASE_URL=postgresql+psycopg://credisure:credisure@db:5432/credisure`, a dummy `JWT_SECRET=dev-only-change-me`, `CORS_ORIGINS=http://localhost:3000`). Add it to the `.gitignore` allow-list.

### 4. API skeleton (`api/`)
- `uv init --app` style project with **`pyproject.toml`**, `requires-python = ">=3.12,<3.13"`, and `uv.lock` committed.
- **Runtime deps:** `fastapi`, `uvicorn[standard]`, `pydantic>=2.9`, `pydantic-settings`, `sqlalchemy>=2.0.36`, `alembic`, `psycopg[binary]>=3.2`, `pyjwt>=2.9`, `bcrypt>=4.2`. Add the latest stable versions at install time, and let the lockfile pin them.
- **Dev deps** (`[dependency-groups] dev`): `pytest`, `pytest-cov`, `httpx`, `ruff`, `mypy`.
- **Tool config in `pyproject.toml`:**
  - ruff: `line-length = 100`, `target-version = "py312"`, lint `select = ["E","F","I","UP","B","SIM","ASYNC","S"]`. Per-file ignores: `tests/**` → `S101, S105, S106, S311`; `scripts/**` → `S105, S106, S311` (demo passwords and the seeded `random` are intentional); `app/providers/simulator.py` → `S311` (simulation, not crypto).
  - mypy: `strict = true` on `app`, with the `pydantic.mypy` plugin.
  - pytest: `testpaths = ["tests"]`, `addopts = "-q --cov=app --cov-report=term-missing"`.
- **Package layout:** create exactly the tree in design §4.1. Every module exists, and anything not used yet holds only a docstring saying which phase fills it in (for example `"""Business query service. Implemented in Phase 3."""`).
- `app/core/config.py`: a `Settings(BaseSettings)` with `database_url` (default `postgresql+psycopg://credisure:credisure@localhost:5433/credisure`), `test_database_url` (default the same but `/credisure_test`), `jwt_secret`, `jwt_ttl_minutes=60`, `cors_origins: list[str]`, `env: Literal["local","test","prod"]="local"`, `pinger_enabled: bool=True`, and `app_version="0.1.0"`, plus a cached `get_settings()`.
- `app/db/session.py`: engine, `SessionLocal`, and a `get_db()` dependency (yields a session and closes it). `app/db/base.py`: `class Base(DeclarativeBase)` with a naming convention for constraints (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`) so Alembic autogenerate gives stable names.
- `app/main.py`: a `create_app()` factory that adds CORS (from settings) and includes the routers. For now that is only `GET /health`, which runs `SELECT 1` and returns `{"status":"ok","db":"ok","version":…,"time":…}`, or **503** with `"db":"down"`. Also define `app = create_app()`.
- **Alembic:** run `alembic init alembic`. `env.py` reads the URL from `get_settings()` and uses `Base.metadata` as `target_metadata` (import `app.models` so models register). No migration files yet.
- `api/Dockerfile`: multi-stage on `python:3.12-slim`. Install uv, `uv sync --frozen --no-dev`, copy the app, run as a non-root user, `EXPOSE 8000`. The CMD is `scripts/start.sh`, which for now runs `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1` (migrate and seed steps arrive in Phase 2).
- `api/.env.example` lists every variable with a comment.
- `tests/conftest.py`: sets `ENV=test` and points `DATABASE_URL` at `test_database_url`, and provides a `client` fixture (`TestClient(create_app())`). `tests/test_health.py` checks that `/health` returns 200 and `db == "ok"`.

### 5. Web skeleton (`web/`)
- `pnpm create next-app@15 web --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-pnpm` (Next.js 15, React 19, Tailwind v4). **Pin 15**: later majors drop `next lint` and change the gotchas these docs describe.
- `pnpm dlx shadcn@latest init` with base color **slate** and CSS variables on. Add these components now so later phases don't stall: `button input label card badge table sheet dialog dropdown-menu select skeleton sonner tooltip separator avatar checkbox popover command scroll-area`.
- **Deps:** `@tanstack/react-query`, `zod`, `react-hook-form`, `@hookform/resolvers`, `next-themes`, `lucide-react`, `recharts`. **Dev:** `prettier`, `prettier-plugin-tailwindcss`, `openapi-typescript`.
- **Scripts in `package.json`:** `dev`, `build`, `start`, `lint`, `typecheck` (`tsc --noEmit`), `format` / `format:check` (prettier), `gen:api` (`openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts`).
- Create the folder tree from design §4.2 with `.gitkeep` files where empty. `src/app/page.tsx` is a placeholder card: "CrediSure Ops Console: Phase 1 skeleton" plus the result of a client-side fetch to `${NEXT_PUBLIC_API_URL}/health`, showing ok or unreachable.
- `web/.env.example` contains `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- `web/Dockerfile`: multi-stage on `node:22-alpine` with `corepack enable`, `pnpm install --frozen-lockfile`, and `pnpm build` with `ARG NEXT_PUBLIC_API_URL`. Use `output: "standalone"` in `next.config.ts`. The runner runs as a non-root user with `EXPOSE 3000`.

### 6. Pre-commit
Hooks: `ruff` (check --fix) + `ruff-format` scoped to `api/`, `prettier` scoped to `web/` (local hook running `pnpm -C web prettier --write`), `end-of-file-fixer`, `trailing-whitespace`, `check-yaml`, `check-added-large-files`, `detect-private-key`.

### 7. CI (`.github/workflows/ci.yml`)
Triggered on `push` and `pull_request`. Two jobs:
- **api:** runs on ubuntu-latest with a `postgres:16` service (user, password and db `credisure`, plus a step that creates `credisure_test`). Uses `astral-sh/setup-uv`, then `uv sync`, `ruff check`, `ruff format --check`, `mypy app`, and `pytest` with `TEST_DATABASE_URL` set.
- **web:** uses `pnpm/action-setup` and `actions/setup-node@v4` (node 22, pnpm cache), then `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm format:check`, `pnpm typecheck`, and `pnpm build` (with `NEXT_PUBLIC_API_URL=http://localhost:8000`).

## Acceptance criteria
1. `git log` on `main` shows the docs commit. All Phase 1 work is on `phase/1-repo-setup`.
2. The tree matches design §4.1 and §4.2. Placeholder modules carry a docstring naming their phase.
3. `make install` succeeds from a clean clone.
4. `make lint` passes. With `make db` running, `make test` passes (the health test).
5. `make web-check` passes.
6. `docker compose up --build` starts all three services. `curl localhost:8000/health` gives 200 `{"status":"ok","db":"ok",…}`, and http://localhost:3000 shows the placeholder with API **ok**.
7. Stopping the db container makes `/health` return 503 `"db":"down"`.
8. No real secrets are committed. `.env.example` files list every variable.
9. CI YAML is valid (run `actionlint` if available, otherwise note that in the report). It won't run until there's a remote.

## Verify
```bash
make install
make lint
make db && make test
make web-check
docker compose up --build -d && sleep 15 && curl -s localhost:8000/health && curl -s -o /dev/null -w "%{http_code}\n" localhost:3000
docker compose stop db && curl -s -w " %{http_code}\n" localhost:8000/health; docker compose start db
docker compose down
```

## Out of scope
Models, migrations, seed, auth, and any real page. Those come in Phases 2+.

## Review checklist (Opus)
- [ ] `.gitignore` doesn't exclude lockfiles or `.env.example` and `.env.docker`. `.env` is excluded.
- [ ] mypy strict actually runs on `app`, and ruff `S` rules are active.
- [ ] The Dockerfiles run as non-root, and the API uses `--workers 1` (ADR-005).
- [ ] Health returns 503 when the db is down, and it doesn't leak the exception text.
- [ ] The Alembic `env.py` URL comes from settings, not `alembic.ini`.
- [ ] The CI api job creates `credisure_test` before pytest.
- [ ] The Next config has `output: "standalone"`. The page doesn't hard-code the API URL.
