# Phase 2 review

- **Branch:** `phase/2-data-auth`
- **Reviewer:** Opus
- **Date:** 2026-11-03
- **Verdict:** Ready to merge

## Verify (re-run by the reviewer)
```text
$ make lint   → ruff, mypy strict ("no issues found in 44 source files"), eslint, prettier: clean
$ make test   → 37 passed, coverage 97% total
$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude'  → 0
```

## Findings
| # | Severity | Area | Finding | Fix |
|---|---|---|---|---|
| 1 | nit | OpenAPI | 422 responses still advertise FastAPI's default `HTTPValidationError` schema, not the envelope | Left as-is. The runtime is correct and the frontend parses the envelope generically. Could be fixed later with a `responses=` override |
| 2 | nit | seed | Stale bank count is 24 against a test floor of 20, which is a thin margin if the RNG draw order changes | Left as-is. The seed is deterministic, and any change shows up in `test_seed` |
| 3 | nit | `/health` | 503 body is not an envelope | Already scheduled for Phase 4 (health is an infra probe, not an API error) |

## Checklist
- [x] No path stores, returns or logs a full BVN or account number. The model has `bvn_last4` and `account_last4` only, with digit CHECK constraints.
- [x] Unknown-email login still runs bcrypt against `DUMMY_HASH`.
- [x] A missing bearer token gives 401 (`HTTPBearer(auto_error=False)`).
- [x] The role is loaded from the DB user on every request.
- [x] The migration creates `citext` and `pg_trgm`, the GIN trigram indexes and the partial failed-check index, and its downgrade drops all 7 enum types.
- [x] The seed is deterministic and has a self-check. Tests leave the test DB empty (rollback isolation).
- [x] 500s are handled inside the request-id middleware, so they keep CORS and `X-Request-ID`. Tracebacks are logged, never returned.

## Accepted deviations
`BCRYPT_ROUNDS` setting (tests use 4), `ttl_minutes` override for tests, the bcrypt 72-byte guard, and `disable_existing_loggers=False` in Alembic. All are sensible.

## Notes for the next phase
- Reuse `factories.make_business` for exact fixtures. The seed output is only for manual checks.
- The reason lists live in `scripts/seed_data.py` today. Phase 4 moves them to `app/services/catalog.py`, and Phase 3 creates `catalog.py` for labels and bands, so put both there.
