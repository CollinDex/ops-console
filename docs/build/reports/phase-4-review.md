# Phase 4 review

- **Branch:** `phase/4-providers-retry-audit`
- **Reviewer:** Opus
- **Date:** 2026-11-03
- **Verdict:** Ready to merge

## Verify (re-run by the reviewer)
```text
$ make lint → mypy "no issues found in 55 source files", ruff, eslint, prettier clean
$ make test → 119 passed
$ pytest tests/test_retry.py -k concurrent, run 5 times → ok ×5
$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude' → 0
```

## Retry walkthrough (design §7.3)
I read `app/services/retry.py` line by line against the design:
- The key is inserted and **committed** in `_claim_key` before any provider work. An `IntegrityError` goes to the replay, 409 or 422 paths, and a replay returns the stored body with `replayed: true` and no provider call or audit row. ✅
- `db.commit()` before the provider call, so no transaction is open while `anyio.from_thread.run` waits on the provider. ✅
- `ProviderUnavailable` and `TimeoutError` become a stored business outcome (200, failed). Any other exception releases the key and re-raises (500). ✅
- The outcome (check, stage, bank sync, audit and stored response) goes into one transaction. ✅
- Accepted beyond the spec: the key is also released if the outcome commit fails. The trade-off (a rare second provider call versus a stuck key) is documented in the implementation report.

## Findings
| # | Severity | Area | Finding | Fix |
|---|---|---|---|---|
| 1 | minor | `services/retry.py` | `assert stored is not None` in production code is stripped under `python -O` | Replaced it with an explicit `RuntimeError` (`fix(api): replace assert with explicit error in retry outcome`) |
| 2 | minor | design §9 | The health contract listed `ok \| degraded` only. The agreed fix (Phase 1 review) is `down` + 503 for a DB outage | Design updated and re-rendered (`docs: document down status for health endpoint`) |
| 3 | nit | header vs role order | An analyst without a key gets 403 rather than 400 | Accepted. Authorisation first is the safer order |

## Checklist
- [x] Key committed before the provider call. The provider is never called inside an open transaction.
- [x] A replay returns the stored body. A different hash gives 422.
- [x] The key is released on unexpected errors and on `check_not_retryable`.
- [x] Threadpool route plus `anyio.from_thread`. The pinger runs DB work through `to_thread`.
- [x] The pinger is disabled in tests, survives errors and DB restarts, and stops on shutdown.
- [x] Simulate is ops_admin only and audited.
- [x] The concurrency test overlaps with a barrier and a 0.3 s provider sleep, and is stable over 5 runs.
- [x] `/health`: 200 `degraded` for provider problems, 503 `down` for a DB outage.

## Notes for the next phase
- Run `pnpm gen:api` against a stack built from this `main`. The retry and provider schemas are now final.
- The retry response has `replayed`, and replays also set the `Idempotent-Replayed: true` header.
