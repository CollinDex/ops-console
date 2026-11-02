# Phase 3: Core data API

| | |
|---|---|
| **Branch** | `phase/3-core-api` |
| **Depends on** | Phase 2 merged |
| **Read first** | design §1.5 (brief coverage), §2.1 (definitions), §6.1–6.3 (endpoints, list semantics, detail), §6.5 (errors) |
| **Estimated effort** | 2–2.5 h |

## Goal
Build the read side of the console: the businesses list (search, filters, sort, pagination), business detail, filter metadata, the overview stats, the staff list, and the CSV export. Every endpoint is role-protected and backed by indexed SQL.

## 1. Shared pieces
- **`app/schemas/common.py`:** `class Page(BaseModel, Generic[T])` with `items: list[T]`, `total: int`, `page: int` and `page_size: int`.
- **Pagination params dependency:** `page: int = Query(1, ge=1)` and `page_size: int = Query(20, ge=1, le=100)`.
- **Search escaping helper:** `like_escape(term)` escapes `\`, `%` and `_`, and is used with `escape="\\"`. Trim the term, and treat an empty term as no search. Cap it at 100 characters (422 above that).
- **Masking helpers** (`app/services/masking.py`): `mask_bvn(last4) -> "*******1234"` (11 digits) and `mask_account(last4) -> "******5678"` (10-digit NUBAN).

## 2. Businesses (`app/services/businesses.py`, `app/api/v1/routers/businesses.py`)

### Filters model
```python
class BusinessFilters(BaseModel):
    search: str | None
    stage: list[Stage] = []
    sector: list[Sector] = []
    score_min: int | None  # 300–850
    score_max: int | None  # 300–850
    failed_check: Literal["any", "cac", "tin", "bvn", "bank_link"] | None
    sort: Literal["name", "credit_score", "created_at", "last_bank_sync_at"] = "created_at"
    order: Literal["asc", "desc"] = "desc"
```
Repeatable query params (`?stage=a&stage=b`) use `Query(default=[])`. Build the model in a dependency so the list and CSV endpoints share it. If `score_min > score_max`, return 422 `validation_error` with field `score_min`.

### `build_business_query(filters) -> Select`
This is the single function behind both the list and the CSV export:
- **search:** `or_(name.ilike(f"%{t}%"), director_name.ilike(f"%{t}%"), cac_number.ilike(f"{t.upper()}%"))`, escaped.
- **stage / sector:** `IN (...)` when non-empty.
- **score range:** inclusive. When either bound is present, NULL scores are excluded.
- **failed_check:** `EXISTS (SELECT 1 FROM verification_checks c WHERE c.business_id = b.id AND c.status = 'failed' [AND c.type = :t])`.
- **Sort:** an allow-listed column map. `credit_score` and `last_bank_sync_at` use **NULLS LAST** in both directions. Always add `Business.id` as the final tie-breaker.

### List: `GET /api/v1/businesses` (analyst, ops_admin; action "view businesses")
- `total` = `select(func.count()).select_from(query.order_by(None).subquery())`.
- Page rows = `query.limit(page_size).offset((page-1)*page_size)`.
- **Checks without N+1:** run one extra query, `SELECT business_id, type, status FROM verification_checks WHERE business_id IN (:page_ids)`, and fold the result into `checks: {"cac": "passed", …}`. That makes 3 queries per request no matter the page size. Don't rely on `selectin` loading of full check objects here, because the list only needs statuses.
- **Item schema `BusinessListItem`:** `id`, `name`, `cac_number`, `sector`, `state`, `stage`, `credit_score`, `checks: dict[CheckType, CheckStatus]`, `has_failed_check: bool`, `last_bank_sync_at`, `bank_data_stale: bool` (bank_link passed and sync more than 7 days old), `created_at`.
- `page` past the end returns 200 with empty `items` and the real `total`.

### Detail: `GET /api/v1/businesses/{id}` (analyst, ops_admin)
- `BusinessDetail` = the list item fields plus `tin`, `director_name`, `bvn_masked`, `bank_name`, `account_masked`, `consent_given_at`, and `checks: list[CheckOut]`. A `CheckOut` has `type`, `status`, `failure_reason`, `attempts` and `updated_at`, ordered cac, tin, bvn, bank_link.
- An invalid UUID or unknown id returns 404 `not_found` with the message "Business not found." (catch the UUID parse error, don't return a 422).
- The response must have **no** `bvn_last4` or `account_last4` fields. It only has the masked strings.

### CSV export: `GET /api/v1/businesses/export.csv` (analyst, ops_admin)
- Declare this route **before** `/{id}` so it isn't swallowed as an id.
- Same filters and sort, no pagination, capped at 10,000 rows (add an `X-Truncated: true` header if the cap is hit).
- Use a `StreamingResponse` with `text/csv; charset=utf-8` and `Content-Disposition: attachment; filename="credisure-businesses-YYYYMMDD.csv"`. Write the rows with the `csv` module into a generator.
- Columns: `name, cac_number, sector, state, stage, credit_score, cac, tin, bvn, bank_link, last_bank_sync_at, joined`. No director name or identifiers (data minimisation).
- Write the audit row `businesses.export` with `details = {"filters": <non-empty filters>, "rows": n}`.

## 3. Meta: `GET /api/v1/meta/filters` (analyst, ops_admin)
```json
{
  "stages":  [{"value": "signed_up", "label": "Signed up"}, …],      // funnel order
  "sectors": [{"value": "agriculture", "label": "Agriculture"}, …],  // alphabetical by label
  "check_types": [{"value": "cac", "label": "CAC"}, {"value": "tin", "label": "Tax ID"}, {"value": "bvn", "label": "BVN"}, {"value": "bank_link", "label": "Bank link"}],
  "score_bands": [{"key": "poor", "label": "Poor", "min": 300, "max": 579}, {"key": "fair", "label": "Fair", "min": 580, "max": 669},
                  {"key": "good", "label": "Good", "min": 670, "max": 739}, {"key": "very_good", "label": "Very good", "min": 740, "max": 799},
                  {"key": "excellent", "label": "Excellent", "min": 800, "max": 850}]
}
```
Define the labels and bands once in `app/services/catalog.py`, and reuse them in stats and CSV.

## 4. Stats: `GET /api/v1/stats/overview` (all roles)
```json
{
  "cards": {"total_businesses": 300, "fully_verified": 120, "stuck": 74, "avg_credit_score": 652.4},
  "funnel": [{"stage": "signed_up", "label": "Signed up", "count": 30}, …],   // all 5 stages, zero-filled, funnel order
  "needs_attention": [
    {"id": "…", "name": "Adebayo Agro Ventures Ltd", "stage": "checks_in_progress",
     "reasons": [{"kind": "failed_check", "check": "bvn", "label": "BVN failed"},
                 {"kind": "stale_bank_data", "days": 12, "label": "Bank data 12 days old"}],
     "since": "2026-10-30T10:00:00Z"}
  ],
  "signups": [{"week_start": "2026-08-17", "count": 14}, …],                 // last 12 ISO weeks (Mon), zero-filled, oldest first
  "generated_at": "…"
}
```
- **Definitions are exactly design §2.1.** The 7-day threshold is a module constant, `STALE_DAYS = 7` / `STUCK_DAYS = 7`.
- `avg_credit_score` covers non-null scores only, rounded to 1 decimal place, or `null` if there are none.
- `needs_attention`: limit 10, ordered by `since` descending. `since` is the newest failed check's `updated_at`, or the `last_bank_sync_at` for stale data.
- Signups use `date_trunc('week', created_at AT TIME ZONE 'Africa/Lagos')`. Zero-fill the missing weeks in Python.
- Use aggregate SQL (`count(*) FILTER (WHERE …)`), not Python loops over all rows. The target is 4 queries or fewer.
- Viewers get the same payload: it contains no personal data (no director names or identifiers).

## 5. Staff: `GET /api/v1/staff` (analyst, ops_admin; action "view the team")
- Params: `search` (name or email ILIKE), `role` (repeatable), `sort` ∈ {`full_name`, `created_at`, `role`}, `order`, plus pagination.
- Returns `Page[StaffOut]`, where a `StaffOut` has `id`, `email`, `full_name`, `role` and `created_at`. **Never** `password_hash`.

## 6. Router wiring
Include all routers in `create_app()` under `/api/v1`, each with a `tags=[…]` entry for tidy OpenAPI. Every response has a `response_model`.

## 7. Tests
Build fixtures with `factories.make_business` so each assertion is exact and doesn't depend on the seed.
- `test_businesses_list.py`:
  - pagination: total, page size, the last partial page, and a page past the end
  - default sort is newest first, and sorting by name ascending works. **NULLS LAST** holds for score in both directions. Ordering stays stable across pages when values tie (no duplicates or gaps over all pages).
  - search: name substring, director name, CAC prefix, case-insensitive, and `%`/`_` taken literally
  - each filter alone, then stage + sector + score range + failed_check combined
  - `failed_check=any` vs `failed_check=bvn`
  - `score_min > score_max` gives 422, and an invalid enum value gives 422 envelope
  - viewer gets 403 and no token gets 401
- `test_business_detail.py`: masked fields only (assert that `"bvn_last4" not in body` and the full mask format), checks ordered, unknown id or garbage id gives 404.
- `test_export.py`: the header row, filters applied, content-disposition, the audit row written, and a viewer gets 403.
- `test_stats.py`: a hand-built fixture of about 10 businesses with known values, asserting every card number, the funnel zero-fill, the needs-attention reasons and order, and the signups zero-fill.
- `test_meta.py` and `test_staff.py`: shapes, role gates, and no `password_hash` key.
- One **query-count** test: use an SQLAlchemy `before_cursor_execute` listener to assert that `GET /businesses?page_size=50` runs 3 statements or fewer (plus the auth user lookup).

## Acceptance criteria
1. Every endpoint in design §6.1 that belongs to this phase works in `/docs` against the seeded data, with the role matrix enforced.
2. `GET /businesses?failed_check=bvn&stage=checks_in_progress` returns only businesses with a failed BVN check in that stage, and `total` matches a manual SQL count.
3. Search finds by business name, director name and CAC prefix.
4. The detail response never contains raw last4 fields.
5. The CSV opens in a spreadsheet, honours the filters, and writes an audit row.
6. The stats numbers match a manual SQL check on the seed (put the SQL and the result in the implementation report).
7. `make lint` and `make test` pass, and the list endpoint makes no N+1 queries.

## Verify
```bash
make lint && make test
docker compose up --build -d && sleep 20
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -H 'content-type: application/json' -d '{"email":"analyst@credisure.demo","password":"Analyst@2026"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s "localhost:8000/api/v1/businesses?failed_check=bvn&stage=checks_in_progress&page_size=5" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -40
curl -s "localhost:8000/api/v1/stats/overview" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -30
curl -s -D - "localhost:8000/api/v1/businesses/export.csv?sector=agriculture" -H "Authorization: Bearer $TOKEN" | head -5
docker compose exec db psql -U credisure -c "select count(*) from businesses b where stage='checks_in_progress' and exists (select 1 from verification_checks c where c.business_id=b.id and c.type='bvn' and c.status='failed');"
```

## Out of scope
Retry, audit read endpoint, providers (Phase 4). Any frontend.

## Review checklist (Opus)
- [ ] The sort column comes only from the allow-list. No f-string SQL anywhere.
- [ ] LIKE escaping is correct, and the CAC search is a prefix match.
- [ ] `total` is computed without ORDER BY, and the pagination tie-breaker is present.
- [ ] The export route is declared before `/{id}`, its audit row is written, and it has no PII columns.
- [ ] The stats definitions match design §2.1 exactly ("stuck" includes the 7-day rule, and "needs attention" requires bank_link passed for staleness).
- [ ] The query-count test exists and passes.
- [ ] Response models stop `password_hash` and the last4 fields from ever serialising.
