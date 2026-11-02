# Phase 4: Providers, idempotent retry & audit

| | |
|---|---|
| **Branch** | `phase/4-providers-retry-audit` |
| **Depends on** | Phase 3 merged |
| **Read first** | design §4.1 (provider adapter interface), §6.4 (retry contract), §6.5 (errors), §7.3 (idempotent retry, **read carefully**), §7.4 (pinger), §9 (observability), ADR-004, ADR-005 |
| **Estimated effort** | 3 h |

## Goal
This phase adds the backend depth: simulated providers behind an adapter interface, a 15-second background health pinger, provider status and incident history, a demo toggle to break a provider, an **idempotent check retry** that never calls a provider twice for one key, and the audit trail for each business.

## 1. Provider adapters (`app/providers/`)
**`base.py`**
```python
@dataclass(frozen=True)
class PingResult:  status: PingStatus; latency_ms: int | None; error: str | None
@dataclass(frozen=True)
class CheckResult: passed: bool; failure_reason: str | None

class VerificationProvider(Protocol):
    name: ProviderName
    async def ping(self) -> PingResult: ...
    async def verify(self, business_id: UUID, check: CheckType) -> CheckResult: ...

CHECK_PROVIDER: dict[CheckType, ProviderName] = {cac: cac, tin: tin, bvn: bvn, bank_link: open_banking}
SLOW_THRESHOLD_MS = 1000
CALL_TIMEOUT_S = 5.0
```

**`simulator.py`: `SimulatedProvider`**
- Constructor: `name`, `rng: random.Random`, `sleep: Callable[[float], Awaitable[None]] = asyncio.sleep`, `pass_rate: float = 0.8`. Injecting `rng` and `sleep` keeps tests deterministic and fast.
- `mode: Literal["up","slow","down"]` starts as `"up"`. `set_mode()` is thread-safe (use a `threading.Lock`).
- Latency: `up` is uniform 80–250 ms, `slow` is uniform 1,200–2,500 ms. `down` sleeps 300 ms and then raises `ProviderUnavailable(name)`.
- `ping()` returns a `PingResult`. Status is `slow` when latency is at least `SLOW_THRESHOLD_MS`, otherwise `up`. When down: `PingResult(down, None, "Connection refused (simulated)")`.
- `verify()` sleeps for the mode's latency, then passes with probability `pass_rate`. Otherwise it fails with a random reason from the **same reason lists the seed uses** (move them to `app/services/catalog.py` and import them in both places). When down it raises `ProviderUnavailable`.
- Count calls in `self.verify_calls` (tests use it to prove "exactly one provider call").

**`registry.py`:** a module-level `ProviderRegistry` holding the four `SimulatedProvider`s (production rng is `random.Random()`), with `get(name)`, `all()` and `for_check(check_type)`. Add a FastAPI dependency `get_registry()` so tests can override it with a fast, seeded registry.

## 2. Pinger (`app/providers/pinger.py`)
- `async def run_pinger(registry, session_factory, interval=15.0, stop: asyncio.Event)` loops until `stop` is set:
  1. `results = await asyncio.gather(*(asyncio.wait_for(p.ping(), CALL_TIMEOUT_S) for p in providers), return_exceptions=True)`. A timeout or exception becomes a `down` ping with `error=str(exc)[:200]`.
  2. Write the 4 `provider_pings` rows in **`await asyncio.to_thread(_insert, …)`** so the sync DB call doesn't block the event loop.
  3. At most once an hour, delete pings older than 7 days and `idempotency_keys` older than 24 h (also through `to_thread`).
  4. Catch and log any exception per iteration. **The loop must never die.**
- Start it in the `create_app()` **lifespan** when `settings.pinger_enabled and settings.env != "test"`. On shutdown, set `stop` and await the task.
- Also expose `async def ping_once(registry, session_factory, names=None)`. The simulate endpoint uses it to record an immediate ping.

## 3. Provider endpoints (`app/api/v1/routers/providers.py`, `app/services/providers.py`)
**`GET /api/v1/providers/status`** (all roles)
```json
{
  "providers": [{
    "name": "bvn", "label": "BVN (NIBSS)", "status": "up", "mode": "up",
    "latency_ms": 143, "last_checked_at": "…",
    "uptime_24h": 99.3, "avg_latency_24h": 171,
    "recent": [{"checked_at": "…", "status": "up", "latency_ms": 140}, …]   // last 40 pings, oldest first, for the sparkline
  }, …],                                                                    // order: bvn, cac, tin, open_banking
  "summary": {"up": 3, "slow": 0, "down": 1},
  "generated_at": "…"
}
```
- Labels: `BVN (NIBSS)`, `CAC registry`, `Tax ID (FIRS)`, `Open banking`.
- The latest ping per provider uses `DISTINCT ON (provider) … ORDER BY provider, checked_at DESC`.
- `uptime_24h` is the percentage of pings in the last 24 h that are not `down` (1 decimal place). `avg_latency_24h` averages successful pings only. Both are `null` if there are no pings.
- A provider with no pings yet gets `status: "unknown"`. Add `unknown` to the response schema only, not to the DB enum.

**`GET /api/v1/providers/{name}/incidents`** (all roles; 404 for an unknown name)
- Scan the last 7 days of pings for that provider in time order, grouping **consecutive non-`up`** pings into incidents: `{"started_at", "ended_at" (null if still ongoing), "duration_seconds", "worst_status": "down"|"slow", "ping_count"}`. Return newest first, limit 20.
- Write the grouping as a pure function, `group_incidents(pings) -> list[Incident]`, and unit-test it.

**`POST /api/v1/providers/{name}/simulate`** (ops_admin only; action "change provider simulation")
- Body `{"mode": "up"|"slow"|"down"}`. Calls `registry.get(name).set_mode(mode)`, writes the audit row `provider.simulate` (`target_type="provider"`, `target_id=name`, `details={"from": old, "to": new}`), commits, then `await ping_once(...)` for that provider so the panel updates straight away. Returns the provider's status object.

**`/health` update:** add `"providers": {"up": n, "slow": n, "down": n}` from the latest pings. Overall `status` is `"degraded"` if any provider's latest ping is `slow` or `down`, but it is still HTTP 200. HTTP 503 is only for a DB outage.

## 4. Idempotent retry (`app/services/retry.py`, route in `routers/businesses.py`)
**Route:** `POST /api/v1/businesses/{id}/checks/{check_type}/retry` (ops_admin only; action "re-run checks"). Declare it as a **sync `def`** route, so FastAPI runs it in a worker thread. From there, call the async provider with `anyio.from_thread.run(...)`. That keeps the sync SQLAlchemy session off the event loop.

**Header:** `Idempotency-Key`. Missing or blank gives 400 `idempotency_key_required`. If it doesn't match `^[A-Za-z0-9_-]{8,128}$`, return 422 `validation_error` (field `header.Idempotency-Key`).

**Algorithm** (each numbered step is one transaction unless marked otherwise):
1. Load the business (404 `not_found`) and the check (404 if the `check_type` is invalid; FastAPI's enum validation already gives 422, so map that path parameter error to 404 `not_found` with the message "Unknown check type.").
2. `request_hash = sha256(f"POST|/businesses/{id}/checks/{type}/retry|{actor_id}")`.
3. **Claim the key:** `INSERT INTO idempotency_keys (key, actor_id, request_hash, response_status=NULL, response=NULL)` and **commit**.
   - On `IntegrityError`: roll back, then `SELECT` the row.
     - different `request_hash` → 422 `idempotency_key_reused`
     - `response IS NULL` → 409 `request_in_progress`
     - otherwise → return the stored `response` with `replayed: true` and the response header `Idempotent-Replayed: true`. **No provider call and no audit row.**
4. **Check eligibility** (after claiming): if `check.status != failed`, delete the key row and return 409 `check_not_retryable` ("Only failed checks can be re-run."). Doing this after the claim means a replay of a *completed* retry still returns its original result even though the check may now be passed.
5. **Call the provider** (outside any DB transaction): `anyio.from_thread.run(_verify_with_timeout, provider, business_id, check_type)`, which wraps `asyncio.wait_for(provider.verify(...), CALL_TIMEOUT_S)`.
   - `ProviderUnavailable` or `TimeoutError` → `CheckResult(False, f"Provider unavailable ({provider.name})")`. This is a business outcome, so the API still returns 200.
   - Any other exception → delete the key row (new transaction), then re-raise (500). That lets the client retry with the same key.
6. **Commit the outcome** in one transaction: update the check (`status`, `failure_reason` cleared if passed, `attempts += 1`, `updated_at`), set `business.stage = derive_stage(...)`, update `last_bank_sync_at = now` if `bank_link` passed, write the audit row `check.retry` (`target_type="business"`, `target_id=id`, `details={"check", "result", "failure_reason", "attempts", "idempotency_key"}`), and set `idempotency_keys.response_status=200, response=<body>`.
7. Return `{"check": CheckOut, "business_stage": Stage, "replayed": false}`.

**Known limitation (by design):** two *different* keys are two separate intents, for example two admins clicking in two tabs, so both run. Idempotency protects one intent from repeats. It doesn't serialise different intents. Don't add row locks for this, but mention it in the README trade-offs.

Add the new error codes (`idempotency_key_required`, `idempotency_key_reused`, `request_in_progress`, `check_not_retryable`) to `app/core/errors.py`.

## 5. Audit read: `GET /api/v1/businesses/{id}/audit` (analyst, ops_admin)
Returns `[{"id", "action", "actor": {"id","full_name","role"} | null, "details", "created_at"}]`, newest first, limit 50, `target_type="business" AND target_id=:id`. A 404 for an unknown business. There are **no** update or delete routes for audit (add a test asserting that `PUT`/`PATCH`/`DELETE` give 405).

## 6. Seed extension
Add `seed_pings(db, now, rng)` to the seed: 7 days at **1-minute** resolution per provider (about 40k rows, inserted in bulk with `insert(ProviderPing)` and a list of dicts in chunks of 5,000). Mostly `up` (latency 80–250 ms), with scripted incidents so the history isn't empty:
- bvn: `down` for 25 minutes yesterday at 14:10 Lagos time
- open_banking: `slow` for 2 hours, 3 days ago
- cac: `down` for 10 minutes, 5 days ago
- tin: two isolated `slow` blips

The seed exits early on a DB that already has data, so after this phase run `make seed ARGS=--reset` (add `ARGS ?=` to the Makefile target) or `docker compose down -v` to pick up the new rows. Mention this in the report.

Also give a handful of seeded businesses existing `check.retry` audit rows from the demo admin, so the drawer timeline isn't empty.

## 7. Tests
Override `get_registry` with a test registry (`rng=Random(1)`, `sleep` that awaits `asyncio.sleep(0)`, `pass_rate` set per test).
- `test_simulator.py`: latency ranges per mode, `down` raises, the slow threshold is classified correctly, and `verify_calls` counts.
- `test_incidents.py`: the pure `group_incidents` cases: none, single, consecutive, ongoing, and slow-then-down giving a `worst_status` of down.
- `test_providers_api.py`: the status shape and summary, `unknown` with no pings, viewer can read but gets 403 on simulate, simulate writes an audit row and an immediate ping, `/health` is degraded when a provider is down, and 404 for an unknown provider.
- `test_retry.py`:
  - missing key → 400, malformed key → 422, analyst → 403, unknown business → 404, check not failed → 409 and the key row is removed
  - happy path: attempts +1, the status updates, the stage is re-derived (the last failing check passes, so `bank_linked`), and one audit row is written
  - **same key twice in sequence** → identical body, the second has `replayed: true` and the header, `verify_calls == 1`, attempts +1 only once, and one audit row
  - same key on a different check → 422 `idempotency_key_reused`
  - provider down → 200, status `failed` with the reason "Provider unavailable (bvn)", and attempts +1
  - an unexpected provider exception → 500, the key row is deleted, and the same key works afterwards
  - **concurrency:** this test needs *committed* data, so use a separate fixture that seeds into the real test DB and truncates afterwards. The provider's `sleep` really waits 0.3 s. Fire two requests with the same key from two threads (`concurrent.futures.ThreadPoolExecutor` with two `TestClient` calls). Assert exactly one non-replayed 200, the other is 409 `request_in_progress`, `verify_calls == 1`, and attempts went up by exactly 1.
- `test_audit_api.py`: the order, actor embedded, a null actor for system rows, 405 for mutation methods, and a viewer gets 403.
- `test_pinger.py`: run `run_pinger` with `interval=0.01` for about 3 iterations against a registry with one down provider. The rows are written, the down row has an error, and the loop survives a provider that raises an unexpected exception.

## Acceptance criteria
1. With the stack running, `POST /providers/bvn/simulate {"mode":"down"}` (admin) makes `/providers/status` show BVN `down` **immediately**, `/health` show `degraded`, and the next pinger cycle keep it down.
2. Retrying a failed BVN check while BVN is down returns 200 with the reason "Provider unavailable (bvn)". After setting BVN back to `up`, a retry with a **new** key re-runs it.
3. Sending the same request twice with the same `Idempotency-Key` gives one provider call, one audit row, and the second response has `replayed: true`.
4. The concurrency test passes reliably (run it 5 times: `pytest tests/test_retry.py -k concurrent --count 5`, or a loop if pytest-repeat isn't installed).
5. `GET /businesses/{id}/audit` shows the retry with the actor's name and role.
6. Incidents show the seeded history for all four providers.
7. The pinger survives a DB restart (`docker compose restart db`): it logs errors and then recovers without restarting the API.
8. `make lint` and `make test` pass.

## Verify
```bash
make lint && make test
docker compose up --build -d && sleep 25
ADMIN=$(curl -s -X POST localhost:8000/api/v1/auth/login -H 'content-type: application/json' -d '{"email":"admin@credisure.demo","password":"Admin@2026"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
BID=$(curl -s "localhost:8000/api/v1/businesses?failed_check=bvn&page_size=1" -H "Authorization: Bearer $ADMIN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["items"][0]["id"])')
curl -s -X POST localhost:8000/api/v1/providers/bvn/simulate -H "Authorization: Bearer $ADMIN" -H 'content-type: application/json' -d '{"mode":"down"}'
curl -s localhost:8000/health
K=$(uuidgen)
curl -s -i -X POST "localhost:8000/api/v1/businesses/$BID/checks/bvn/retry" -H "Authorization: Bearer $ADMIN" -H "Idempotency-Key: $K"
curl -s -i -X POST "localhost:8000/api/v1/businesses/$BID/checks/bvn/retry" -H "Authorization: Bearer $ADMIN" -H "Idempotency-Key: $K"
curl -s "localhost:8000/api/v1/businesses/$BID/audit" -H "Authorization: Bearer $ADMIN" | python3 -m json.tool | head -30
curl -s localhost:8000/api/v1/providers/bvn/incidents -H "Authorization: Bearer $ADMIN" | python3 -m json.tool | head -20
curl -s -X POST localhost:8000/api/v1/providers/bvn/simulate -H "Authorization: Bearer $ADMIN" -H 'content-type: application/json' -d '{"mode":"up"}'
```

## Out of scope
Any UI. Real provider adapters. Multi-instance pinger coordination (ADR-005).

## Review checklist (Opus)
- [ ] The key row is committed **before** the provider call. The provider is never called inside an open DB transaction.
- [ ] A replay returns the stored body without calling the provider or writing an audit row. A different hash gives 422.
- [ ] The key row is deleted on unexpected errors and on `check_not_retryable`.
- [ ] Route and DB calls run in the threadpool. The pinger uses `to_thread` for DB work and nothing blocks the event loop.
- [ ] The pinger catches per iteration and stops cleanly on shutdown. It's disabled in tests.
- [ ] Simulate is ops_admin only and audited. Viewers can read status.
- [ ] The concurrency test actually overlaps the requests (provider sleep > 0) and isn't flaky.
- [ ] `/health` stays 200 when degraded and is 503 only for a DB outage.
- [ ] The failure reasons come from one shared catalogue.
