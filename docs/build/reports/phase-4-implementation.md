# Phase 4 implementation report

- **Branch:** `phase/4-providers-retry-audit`
- **Implementer:** Sonnet
- **Date:** 2026-11-03
- **Commits:**
```text
91cad38 feat(api): seed provider pings and retry audit rows
14c6e83 test(api): add provider, retry, audit and pinger tests
8d44280 feat(api): add idempotent check retry and business audit endpoint
c6bf44e feat(api): add provider status, incidents and simulate endpoints
5e5a8a5 feat(api): add simulated providers and pinger
```
(plus `docs: add phase 4 implementation report`)

## Summary
Added the simulated providers behind the adapter interface, the 15 s pinger (started in the lifespan, off in tests), provider status / incidents / simulate endpoints, the new `/health` shape, the idempotent check retry, and the business audit endpoint. The seed now writes 7 days of 1-minute pings with scripted incidents and 12 `check.retry` audit rows. 47 new tests; 119 pass in total.

## Acceptance criteria
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Simulate bvn down shows `down` immediately, `/health` degraded, next pinger cycle keeps it down | ✅ | Verify output below: simulate response is `down`, `/health` is `degraded`, then two later pinger rows are `down` |
| 2 | Retry while down returns 200 "Provider unavailable (bvn)"; after `up`, a new key re-runs | ✅ | Verify output below (attempts 3, reason "Provider unavailable (bvn)"); later new keys re-ran the provider (attempts 4 and 5). `test_provider_down_is_a_200_failure_then_new_key_reruns` |
| 3 | Same key twice: one provider call, one audit row, second has `replayed: true` | ✅ | Verify output below (`idempotent-replayed: true`, one audit row); `test_same_key_twice_replays_without_second_call` asserts `verify_calls == 1` |
| 4 | Concurrency test passes reliably (5 runs) | ✅ | 10 consecutive runs, all passed (below) |
| 5 | Audit shows the retry with the actor's name and role | ✅ | Verify output: `Adaeze Okafor`, `ops_admin` |
| 6 | Incidents show seeded history for all four providers | ✅ | bvn 25 min down, cac 10 min down, open_banking 120 min slow, tin 2 slow blips (output below) |
| 7 | Pinger survives a DB restart | ✅ | Stopped and restarted `db`: one `pinger iteration failed` ERROR log, then new pings resumed without restarting the API |
| 8 | `make lint` and `make test` pass | ✅ | Output below |

## Verify output
```text
$ make lint && make test
(api) ruff: All checks passed! · ruff format: 81 files already formatted
(api) mypy: Success: no issues found in 55 source files
(web) eslint clean · prettier: All matched files use Prettier code style!
119 passed, 1 warning in 22.68s        coverage TOTAL 1371 stmts, 19 missed, 99%
```

Concurrency test, 10 runs (`pytest-repeat` is not installed, so a shell loop):
```text
$ for i in 1..10; do uv run pytest tests/test_retry.py -k concurrent --no-cov; done
run 1: 1 passed, 15 deselected   run 2: 1 passed   run 3: 1 passed   run 4: 1 passed   run 5: 1 passed
run 6: 1 passed   run 7: 1 passed   run 8: 1 passed   run 9: 1 passed   run 10: 1 passed   (~0.8 s each)
```

Seed (after `make seed ARGS=--reset`):
```text
staff: 15  businesses: 300  checks: 1200
failed checks: bank_link=19, bvn=36, cac=15, tin=11
stale bank syncs (>7 days): 35
provider pings: 40320  retry audit rows: 12
```

Stack run (`docker compose up --build -d api`; db was already up; the web image was not rebuilt, since nothing in `web/` changed):
```text
$ simulate bvn down
{"name":"bvn","label":"BVN (NIBSS)","status":"down","mode":"down","latency_ms":null,"last_checked_at":"2026-11-02T23:46:30.099943Z","uptime_24h":98.2,"avg_latency_24h":163,"recent":[ …40 points, oldest first, last one "status":"down" ]}
$ curl /health
{"status":"degraded","db":"ok","providers":{"up":3,"slow":0,"down":1},"version":"0.1.0","time":"2026-11-02T23:46:30.177002+00:00"}
$ retry #1 (key 2C4767DF-A5C2-46A3-8F87-654BA65C34F2)
HTTP/1.1 200 OK
x-request-id: 29c2d34eb7d04e60ac96aceddfb18e78
{"check":{"type":"bvn","status":"failed","failure_reason":"Provider unavailable (bvn)","attempts":3,"updated_at":"2026-11-02T23:46:30.507672Z"},"business_stage":"checks_in_progress","replayed":false}
$ retry #2 same key
HTTP/1.1 200 OK
idempotent-replayed: true
{"check":{"type":"bvn","status":"failed","failure_reason":"Provider unavailable (bvn)","attempts":3,"updated_at":"2026-11-02T23:46:30.507672Z"},"business_stage":"checks_in_progress","replayed":true}
$ audit
[{"id": 15, "action": "check.retry",
  "actor": {"id": "134c6c92-…", "full_name": "Adaeze Okafor", "role": "ops_admin"},
  "details": {"check": "bvn", "result": "failed", "attempts": 3,
              "failure_reason": "Provider unavailable (bvn)",
              "idempotency_key": "2C4767DF-A5C2-46A3-8F87-654BA65C34F2"},
  "created_at": "2026-11-02T23:46:30.514260Z"}]
$ incidents bvn
[{"started_at": "2026-11-02T23:46:30.099943Z", "ended_at": null, "duration_seconds": 0, "worst_status": "down", "ping_count": 1},
 {"started_at": "2026-11-02T13:10:00Z", "ended_at": "2026-11-02T13:35:00Z", "duration_seconds": 1500, "worst_status": "down", "ping_count": 25}]
$ simulate bvn up
{"name":"bvn","label":"BVN (NIBSS)","status":"up","mode":"up","latency_ms":200, … }

AC1, next pinger cycles stay down (provider_pings, newest first):
 bvn | down | Connection refused (simulated) | 23:47:09.885
 bvn | down | Connection refused (simulated) | 23:46:54.577
 bvn | down | Connection refused (simulated) | 23:46:43.376
 bvn | up   |                                | 23:46:39.254   <- before the toggle
status: [('bvn','down','down'),('cac','up','up'),('tin','up','up'),('open_banking','up','up')] {'up': 3, 'slow': 0, 'down': 1}

AC2, mode set back to up, six different new keys in a row:
 {"check":{"type":"bvn","status":"failed","failure_reason":"BVN record not found","attempts":4,…},"replayed":false}
 {"check":{"type":"bvn","status":"passed","failure_reason":null,"attempts":5,…},"replayed":false}
 {"error":{"code":"check_not_retryable","message":"Only failed checks can be re-run.",…}}   x4
 audit: check.retry Adaeze Okafor ops_admin passed 5 / failed 4 / failed 3

AC6, incidents per provider (worst_status, seconds, pings):
 bvn: [down 28s 3 pings (my toggling), down 0s, down 1500s 25 pings (seeded)]
 cac: [down 600s 10]   tin: [slow 120s 2, slow 120s 2]   open_banking: [slow 7200s 120]

AC7, DB outage:
 docker compose stop db  -> api log: "pinger iteration failed" (ERROR, logger app.providers.pinger)
 docker compose start db -> new pings for all four providers at 23:48:10, API never restarted; /health ok
 (an earlier plain `docker compose restart db` also left the pinger writing)
```
The stack is stopped (`docker compose stop`; the volume is kept).

## Files added or changed
- **Providers:** `app/providers/{base,simulator,registry,pinger}.py`. `registry.py` also holds `get_registry`.
- **Services and schemas:** `services/{providers,retry,audit,catalog}.py`; `schemas/{providers,audit,retry}.py`. `FAILURE_REASONS` moved to `catalog.py` (the seed imports it from there), with `PROVIDER_LABELS` added.
- **Routers:** `routers/providers.py` (new), `routers/businesses.py` (audit and retry), `routers/health.py`. Also `core/errors.py` (4 new codes), `db/session.py` (`get_session_factory` dependency), `main.py` (lifespan starts the pinger), `pyproject.toml` (S311 ignored in `registry.py`, as already done for the simulator).
- **Seed:** `scripts/seed.py` (`seed_pings`, `seed_retry_audit`, scripted incidents). They use a separate rng stream, so the businesses are unchanged from Phase 3. After this phase run `make seed ARGS=--reset` (the `ARGS ?=` Makefile variable already existed) or `docker compose down -v`.
- **Tests:** `test_simulator`, `test_incidents`, `test_providers_api`, `test_retry`, `test_audit_api`, `test_pinger`, plus a seed test and conftest fixtures (`registry`, `admin_headers`, `SharedSession`).

## Deviations / questions
1. **`run_pinger` signature.** The spec lists `interval=15.0, stop` (a non-default after a default is invalid). I made it `run_pinger(registry, session_factory, *, stop, interval=15.0)`.
2. **Simulate is a sync route.** It calls `anyio.from_thread.run(ping_once, …)` for the immediate ping, as in the retry route. `ping_once` takes a session factory, which is a `get_session_factory` dependency so tests can redirect it to the test session.
3. **Incident bounds.** `ended_at` is the timestamp of the first `up` ping after the run. A run that reaches the end of the data has `ended_at: null` and its duration runs to now. A one-ping incident therefore lasts one ping interval.
4. **Key released on commit failure.** If the outcome transaction (step 6) fails after the provider call, I also delete the key, so the client can retry. The spec only says to do this for step 5. The cost is a possible second provider call in that rare case; otherwise the key would sit "in progress" for 24 h.
5. **Key released when the check row is missing** (not only when not failed), same as `check_not_retryable`.
6. **Header validation runs after the role check**, so an analyst without a key gets 403, not 400.
7. `distinct_on` (SQLAlchemy 2.1 `.ext(...)`) replaces the deprecated `.distinct(col)` for the latest-ping query.
8. The `web` image was not rebuilt for the stack run (no `web/` changes). The first `docker compose up --build` stalled on the base-image pulls; once the `python:3.12-slim` and `uv` images were cached the api built normally.
9. **Design doc note, not edited:** §9 and the spec disagree slightly about `/health.status` on a DB outage ("degraded" or "down"). I followed the spec (`down`, 503).

## Known gaps / follow-ups
- Different keys mean separate intents and both run (by design, noted in the spec). The README trade-offs section is a Phase 7 item.
- `pytest-repeat` is not installed. The `--count 5` command in the spec was replaced by a shell loop.
- Reviewer: check `retry.py` closely. The commits are `_claim_key` (commit before the provider), the explicit `db.commit()` that ends the read transaction before `anyio.from_thread.run`, and `_release_key` on the error paths.
