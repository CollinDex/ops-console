# Phase 3 review

- **Branch:** `phase/3-core-api`
- **Reviewer:** Opus
- **Date:** 2026-11-03
- **Verdict:** Ready to merge after the fix below

## Verify (re-run by the reviewer)
```text
$ make test  → 72 passed, coverage 98%
$ make seed ARGS=--reset → businesses 300, stale bank syncs 35
$ psql: stuck = 123 (was 187 before the fix)
$ git log --format=%B main..HEAD | grep -ci 'co-authored\|claude' → 0
```

## Findings
| # | Severity | Area | Finding | Fix |
|---|---|---|---|---|
| 1 | major | `api/scripts/seed.py` (product realism) | "Stuck in onboarding" was **187 of 300 (62%)**. Business ages were drawn independently of stage, so many 3-month-old businesses sat at `signed_up` and got flagged by the 7-day rule. The headline card would look broken in a demo | Age now depends on stage (`STAGE_AGE_DAYS`: early stages are recent, profile-ready ones are older). Stuck is now **123 (41%)**, mostly real failed checks. The stale-bank probability went from 0.2 to 0.3 to keep a healthy margin (35 rows). Commit `fix(api): age seeded businesses by onboarding stage` |
| 2 | nit | stats `since` | For a business with both a failed check and stale data, `since` is the failed check time | Accepted. The failed check is the more urgent signal |
| 3 | nit | export | The formula-injection guard (`= + - @` get a `'` prefix) wasn't in the spec | Accepted. It's a good security addition |

## Checklist
- [x] Sort column only from `_SORT_COLUMNS`. No f-string SQL.
- [x] LIKE escaping with `escape="\\"`. CAC is a prefix match.
- [x] `count_businesses` strips ORDER BY. `Business.id` tie-breaker.
- [x] `/export.csv` is declared before `/{business_id}`. It writes an audit row and has no PII columns.
- [x] The stats definitions match design §2.1 (staleness requires bank_link passed).
- [x] The query-count test exists. List = count + page + checks.
- [x] Response models exclude `password_hash` and the last4 fields.

## Notes for the next phase
- The seed changed: anyone with an existing volume should run `make seed ARGS=--reset`.
- Phase 4 extends the seed with pings and retry audit rows. Keep the `STAGE_AGE_DAYS` logic.
