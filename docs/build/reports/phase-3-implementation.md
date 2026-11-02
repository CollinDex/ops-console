# Phase 3 implementation report

- **Branch:** `phase/3-core-api`
- **Implementer:** Sonnet
- **Date:** 2026-11-03
- **Commits:** (`git log --oneline main..HEAD`)
  - `feat(api): add shared pagination, search and masking helpers`
  - `feat(api): add businesses list, detail and csv export`
  - `feat(api): add filter meta and staff endpoints`
  - `feat(api): add overview stats endpoint`
  - `docs: add phase 3 implementation report`

## Summary
Built the read side of the console: businesses list (search, filters, sort, offset pagination, batched check statuses), detail with masked identifiers, streamed CSV export with an audit row, filter metadata, overview stats (4 SQL queries) and the staff list. All are role-protected and have `response_model`s. 35 new tests (72 total, 98% coverage).

## Acceptance criteria
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Every §6.1 endpoint in this phase works against the seed, role matrix enforced | ✅ | Verify curls below; role gates covered in each test file (viewer 403, anonymous 401) |
| 2 | `failed_check=bvn&stage=checks_in_progress` returns only matching rows and `total` matches manual SQL | ✅ | API `total 36`, SQL count 36 |
| 3 | Search finds by name, director name and CAC prefix | ✅ | `test_search_by_name_director_and_cac_prefix` |
| 4 | Detail never contains raw last4 fields | ✅ | `test_detail_masks_identifiers_and_orders_checks` |
| 5 | CSV honours filters and writes an audit row | ✅ | `test_export.py`; live: 25 agriculture rows, audit `{"rows": 25, "filters": {"sector": ["agriculture"]}}` |
| 6 | Stats numbers match manual SQL on the seed | ✅ | SQL cross-check below (cards, funnel, signups, top needs-attention) |
| 7 | `make lint`, `make test` pass, no N+1 | ✅ | Output below; `test_list_query_count_does_not_grow_with_page_size` (count, page, checks, plus the auth lookup) |

## Verify output
```text
$ make lint
All checks passed!
72 files already formatted
Success: no issues found in 52 source files
(eslint clean; prettier: All matched files use Prettier code style!)

$ make test
72 passed, 1 warning in 8.66s     (coverage TOTAL 98%)

$ docker compose up --build -d && sleep 20
 ops-console-api-1  Up   0.0.0.0:8000->8000/tcp
 ops-console-db-1   Up (healthy)   0.0.0.0:5433->5432/tcp
 (api log: "Seed skipped: staff_users already has rows"; 300 businesses present)

$ curl ".../businesses?failed_check=bvn&stage=checks_in_progress&page_size=5"   (head)
{"items": [{"id": "56a0b8b4-...", "name": "Arewa Agro Nigeria Ltd", "cac_number": "RC7883425",
 "sector": "agriculture", "state": "Enugu", "stage": "checks_in_progress", "credit_score": 764,
 "has_failed_check": true, "last_bank_sync_at": null, "bank_data_stale": false,
 "created_at": "2026-11-02T20:04:50.114931Z",
 "checks": {"cac": "pending", "tin": "passed", "bvn": "failed", "bank_link": "pending"}}, ...
 total: 36, 5 items

$ curl ".../stats/overview"   (head)
cards: {'total_businesses': 300, 'fully_verified': 120, 'stuck': 187, 'avg_credit_score': 655.6}
funnel: signed_up 30, documents_submitted 36, checks_in_progress 114, bank_linked 45, profile_ready 75

$ curl -D - ".../businesses/export.csv?sector=agriculture" | head -5
HTTP/1.1 200 OK
content-disposition: attachment; filename="credisure-businesses-20261102.csv"
content-type: text/csv; charset=utf-8

$ psql: select count(*) from businesses b where stage='checks_in_progress' and exists (... bvn failed)
 count
-------
    36
```

### Manual SQL cross-check of the stats (run against the seeded DB)
```sql
select count(*) total,
 count(*) filter (where (select count(*) from verification_checks c where c.business_id=b.id and c.status='passed')=4) fully_verified,
 count(*) filter (where stage<>'profile_ready' and (exists(select 1 from verification_checks c where c.business_id=b.id and c.status='failed') or created_at < now()-interval '7 days')) stuck,
 round(avg(credit_score),1) avg_score
from businesses b;
-- total 300 | fully_verified 120 | stuck 187 | avg_score 655.6        (API: identical)

select stage, count(*) from businesses group by stage;
-- signed_up 30, documents_submitted 36, checks_in_progress 114, bank_linked 45, profile_ready 75   (API: identical)

select date_trunc('week', created_at at time zone 'Africa/Lagos')::date, count(*) ... last 12 weeks;
-- 08-17:6, 08-24:16, 08-31:13, 09-07:12, 09-14:17, 09-21:18, 09-28:19, 10-05:15, 10-12:22, 10-19:26, 10-26:62, 11-02:11   (API: identical)

select b.name, max(c.updated_at) filter (where c.status='failed') since ... order by since desc limit 3;
-- Arewa Agro Nigeria Ltd 21:12:11, Balogun Packaging ... 21:08:56, Naija Stores Enterprises 14:02:27   (API top 3: identical)

select count(*) needs_attention ...;  -- 80 (API returns the first 10 of these)
```
Compose stack stopped afterwards (`docker compose down`; the named DB volume is kept).

## Files added or changed
- **Shared:** `app/api/deps.py` (pagination, `like_escape`, search cleaning), `app/schemas/common.py` (`Page`), `app/services/masking.py`, `app/services/catalog.py` (labels, score bands).
- **Businesses:** `app/schemas/business.py`, `app/services/businesses.py` (`build_business_query`, batched statuses, CSV), `app/api/v1/routers/businesses.py`.
- **Meta, staff, stats:** `app/schemas/{meta,staff,stats}.py`, `app/services/stats.py`, routers `meta.py`, `staff.py`, `stats.py`; routers wired in `app/main.py`.
- **Tests:** `test_businesses_list.py`, `test_business_detail.py`, `test_export.py`, `test_stats.py`, `test_meta.py`, `test_staff.py`; `analyst_headers` and `viewer_headers` fixtures added to `conftest.py`.

## Deviations / questions
- **Seed `stuck` is 187, not the 74 in the spec's sample JSON.** The example is illustrative. 187 is what design §2.1 gives on the seed (verified by independent SQL), because the seed spreads signups over 120 days.
- **`since` when a business has both a failed check and stale data** uses the newest failed check's `updated_at` (the spec doesn't say). The reasons list shows both.
- **`Page[T]`** uses PEP 695 syntax (`class Page[T](BaseModel)`), as the codebase already uses `def pg_enum[E: ...]`.
- **Filters dependency** takes `sort`, `order` and `failed_check` as regex-patterned query strings (so the 422 envelope names the field) and builds `BusinessFilters` in the dependency. List params default to `None` rather than `[]` to avoid a mutable default.
- **CSV hardening (small addition):** cells starting with `= + - @` are prefixed with `'` to block spreadsheet formula injection.
- **Lagos weeks:** Python uses a fixed UTC+1 offset (no DST in Lagos) to avoid needing a tzdata package. SQL uses `AT TIME ZONE 'Africa/Lagos'` as specified.
- **List query uses `lazyload(Business.checks)`**, not `noload` (deprecated in SQLAlchemy 2.1), so the `selectin` loader doesn't add a statement.
- The query-count test asserts 3 business queries (count, page, checks) and at most 4 statements overall (plus the auth user lookup).
- The `X-Truncated` test patches the cap down to 2 rather than inserting 10,001 rows.

## Known gaps / follow-ups
- `since` for stale-only businesses is `last_bank_sync_at`, as specified. The stale-bank `days` value is floor(days).
- No `GET /businesses/{id}/audit` (Phase 4).
- Reviewer: check the `stuck` definition (signed up "more than 7 days ago" is `created_at < now - 7d`, strict).
