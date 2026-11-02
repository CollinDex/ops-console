# Phase 2 implementation report

- **Branch:** `phase/2-data-auth`
- **Implementer:** Sonnet
- **Date:** 2026-11-03
- **Commits:**
```text
<report commit> docs: add phase 2 implementation report
c7cb3ae test(api): add db-backed fixtures and auth, error, role tests
65b11ae feat(api): add deterministic seed and migrate-seed startup
7368ca8 feat(api): add error envelope, request id, jwt login and role checks
805e98e feat(api): add stage derivation with exhaustive tests
b393312 feat(api): add data models and initial migration
```

## Summary
Added all six tables as typed SQLAlchemy 2 models (native Postgres enums) with one hand-edited Alembic migration (extensions, trigram and partial indexes, named constraints, enum cleanup on downgrade). Built the error envelope with request-id middleware and JSON logs, bcrypt + HS256 JWT login with `/auth/me` and `require_roles`, a deterministic seed (15 staff, 300 businesses, 1,200 checks), and 37 Postgres-backed tests.

## Acceptance criteria
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Fresh `docker compose up --build` migrates, seeds, serves; a restart does not re-seed | ✅ | After `down -v`, api log shows migration + seed summary; after `docker compose restart api` the log shows "Seed skipped" |
| 2 | Login returns a token; `/auth/me` returns the admin | ✅ | curl output below |
| 3 | Wrong password gives 401 `invalid_credentials` envelope | ✅ | curl output below |
| 4 | Every error response matches the envelope | ✅ | 401/404/405/422/500 covered by tests and curl. Exception: `/health` 503 (Phase 1 body, see Deviations) |
| 5 | `alembic downgrade base && upgrade head` succeeds | ✅ | output below; `alembic check` reports no drift |
| 6 | Seed twice gives same data | ✅ | `--reset` re-run: first 10 businesses by CAC identical (diff empty); also `test_seed_is_deterministic` |
| 7 | `make lint` and `make test` pass; coverage >= 85% on `app/core` and `app/services` | ✅ | 37 passed; core/services files all 94-100%, total 97% |
| 8 | `/docs` shows login and me with correct schemas | ✅ | `/docs` returns 200; openapi paths `/api/v1/auth/login`, `/api/v1/auth/me`; schemas LoginRequest, LoginResponse, UserOut, Role |

## Verify output
```text
$ make db && make migrate && cd api && uv run alembic downgrade base && uv run alembic upgrade head && cd ..
INFO  [alembic.runtime.migration] Running upgrade  -> 649689db837a, initial schema
INFO  [alembic.runtime.migration] Running downgrade 649689db837a -> , initial schema
INFO  [alembic.runtime.migration] Running upgrade  -> 649689db837a, initial schema

$ make seed ARGS=--reset      (make seed on an already-seeded DB prints the skip line)
staff: 15  businesses: 300  checks: 1200
stages: profile_ready=75, bank_linked=45, checks_in_progress=114, signed_up=30, documents_submitted=36
failed checks: bank_link=19, bvn=36, cac=15, tin=11
stale bank syncs (>7 days): 24
$ make seed
Seed skipped: staff_users already has rows (use --reset to rebuild).

$ make lint
All checks passed!
58 files already formatted
Success: no issues found in 44 source files
(web) eslint clean; prettier: All matched files use Prettier code style!

$ make test
37 passed, 1 warning in 2.26s
app/core/errors.py      79  5  94%     app/core/logging.py     27  0  100%
app/core/middleware.py  24  0 100%     app/core/security.py    56  2   96%
app/services/audit.py    6  0 100%     app/services/stage.py   10  0  100%
TOTAL                  483 16  97%

$ docker compose up --build -d && sleep 20
(api log on first boot after down -v)
INFO  [alembic.runtime.migration] Running upgrade  -> 649689db837a, initial schema
staff: 15  businesses: 300  checks: 1200 ...

$ TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login ...admin...)    # token length 268
$ curl -s localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
{"id":"134c6c92-ec5b-427c-9fde-4fbf3ff350bf","email":"admin@credisure.demo","full_name":"Adaeze Okafor","role":"ops_admin"}

$ curl -s -X POST localhost:8000/api/v1/auth/login ... '{"email":"admin@credisure.demo","password":"nope"}'
HTTP/1.1 401 Unauthorized   x-request-id: 81817563497b47d980fe9c35227031fb
{"error":{"code":"invalid_credentials","message":"Email or password is incorrect.","request_id":"81817563497b47d980fe9c35227031fb"}}

$ curl -s localhost:8000/api/v1/auth/me
{"error":{"code":"not_authenticated","message":"Authentication is required.","request_id":"f5f0e59d7b5446b4bed587035355d85f"}}

$ docker compose exec db psql -U credisure -c "select stage, count(*) from businesses group by 1 order by 1;"
        stage        | count
---------------------+-------
 signed_up           |    30
 documents_submitted |    36
 checks_in_progress  |   114
 bank_linked         |    45
 profile_ready       |    75
```
Extra checks: `curl .../api/v1/zzz` gives the 404 envelope; bad login body gives 422 `validation_error` with `details` `[{"field":"body.email",...},{"field":"body.password",...}]`; `docker compose restart api` log shows "Seed skipped"; `alembic check`: "No new upgrade operations detected."; test DB has 0 rows in businesses, staff_users and audit_log after the test run (rollback isolation works). Stack was stopped with `docker compose down` (the `db-data` volume is kept and holds the seeded data).

## Files added or changed
- **Models / DB:** `api/app/models/{enums,_types,staff_user,business,verification_check,provider_ping,audit_log,idempotency_key,__init__}.py`; `api/alembic/versions/649689db837a_initial_schema.py`; `api/alembic/env.py` (`disable_existing_loggers=False`).
- **Core:** `api/app/core/{errors,logging,middleware,security,config}.py`, `api/app/main.py`.
- **Services / schemas / routes:** `api/app/services/{stage,audit}.py`, `api/app/schemas/auth.py`, `api/app/api/v1/routers/auth.py`.
- **Seed / startup:** `api/scripts/{seed,seed_data}.py`, `api/scripts/start.sh`.
- **Tests:** `api/tests/{conftest,factories,test_stage,test_auth,test_errors,test_roles,test_seed}.py`.
- **Config:** `api/pyproject.toml` (email-validator dependency, `slow` marker, S107 ignored in tests), `api/uv.lock`, `api/.env.example` (`BCRYPT_ROUNDS`).

## Deviations / questions
1. **`BCRYPT_ROUNDS` setting** (default 12, spec value). Tests set it to 4 so the suite stays fast; production and the seed use 12.
2. **`idempotency_keys` model and table are created in Phase 2**, because the phase doc says "all six tables". The stub file said Phase 4. Phase 4 only needs to add logic.
3. **`create_access_token(user, ttl_minutes=None)`** takes an optional TTL so tests can build expired tokens, as the spec asks for.
4. **Over-72-byte passwords:** bcrypt 5 raises on them. `verify_password` returns False (so login gives 401); the schema still allows up to 128 chars.
5. **`.test` email TLD** is rejected by `email-validator`, so test factories use `@credisure.demo`.
6. **`alembic/env.py`:** `fileConfig` ran with `disable_existing_loggers=True`, which silenced app loggers when tests ran Alembic in-process. Set to False.
7. **500 handling** sits in the request-id middleware (inside CORS) as well as being registered via `add_exception_handler(Exception, ...)`. This keeps CORS and `X-Request-ID` headers on 500s. Uvicorn's own access log is disabled (`--no-access-log`, plus the logger is disabled) in favour of the JSON access log.
8. The trigram indexes are declared on the model as well as in the migration so `alembic check` has no drift.
9. **Design observation (not changed):** `/health` 503 still returns the Phase 1 body, not the envelope (the Phase 1 review defers this to Phase 4). OpenAPI shows FastAPI's default `HTTPValidationError` for 422 rather than the envelope shape.
10. Unique constraint on checks is named `uq_verification_checks_business_id_type` (the naming convention would otherwise drop the `type` part).

## Known gaps / follow-ups
- Stale-bank count in the seed is 24, close to the >= 20 floor. It is deterministic, but a tweak to the RNG draw order would move it.
- The suite takes about 2 s; seed tests take under 1 s at bcrypt cost 4.
- Pre-commit hooks passed on every commit without reformatting.
