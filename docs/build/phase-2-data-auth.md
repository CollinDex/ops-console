# Phase 2: Data model, seed & authentication

| | |
|---|---|
| **Branch** | `phase/2-data-auth` |
| **Depends on** | Phase 1 merged |
| **Read first** | design §2.1 (definitions), §5 (data model, all of it), §6.5 (error envelope), §7.1–7.2 (login and protected request flows), §8 (security), ADR-003, ADR-006 |
| **Estimated effort** | 2.5–3 h |

## Goal
All six tables exist through an Alembic migration. A deterministic seed fills them with realistic Nigerian SME data. Every error uses the envelope. Staff can log in and get a JWT, and role checks protect routes. This is the foundation every later phase builds on.

## 1. Models (`app/models/`)
One file per table, SQLAlchemy 2 typed style (`Mapped[...]`, `mapped_column`). Enums are Python `StrEnum`s in `app/models/enums.py`, stored as **native Postgres enums** (`sa.Enum(MyEnum, name="…", values_callable=lambda e: [m.value for m in e])`).

| Enum | Values |
|---|---|
| `Role` | `ops_admin`, `analyst`, `viewer` |
| `Stage` | `signed_up`, `documents_submitted`, `checks_in_progress`, `bank_linked`, `profile_ready` (**keep this order**: it is the funnel order) |
| `CheckType` | `cac`, `tin`, `bvn`, `bank_link` |
| `CheckStatus` | `pending`, `passed`, `failed` |
| `Sector` | `agriculture`, `retail`, `manufacturing`, `logistics`, `technology`, `healthcare`, `hospitality`, `construction`, `fashion`, `education` |
| `ProviderName` | `bvn`, `cac`, `tin`, `open_banking` |
| `PingStatus` | `up`, `slow`, `down` |

Use the columns, types, constraints and indexes from design §5.1 and §5.4 exactly, plus these clarifications:
- UUID primary keys use `server_default=sa.text("gen_random_uuid()")`. `provider_pings.id` and `audit_log.id` are `BigInteger` identity columns.
- Every `created_at` and `updated_at` is `timestamptz` with `server_default=now()`. `verification_checks.updated_at` also has `onupdate=now()`.
- `staff_users.email` is `CITEXT`. `businesses.state` is `Text` (36 states + FCT are validated in the seed, not with an enum).
- `bvn_last4` and `account_last4` are `String(4)` with a `CHECK (col ~ '^[0-9]{4}$')`.
- `credit_score` is a nullable `SmallInteger` with `CHECK (credit_score BETWEEN 300 AND 850)`. It is NULL for `signed_up` and `documents_submitted`.
- `verification_checks.attempts` is `Integer`, default 0, with `CHECK (attempts >= 0)`. `business_id` has an FK with `ondelete=CASCADE`.
- `audit_log.actor_id` is a **nullable** FK to `staff_users` (a failed login has no actor). `details` is `JSONB`, default `{}`.
- `idempotency_keys`: composite PK `(key, actor_id)`, `key` is `String(128)`, `request_hash` is `String(64)`, `response_status` is a nullable `SmallInteger`, `response` is nullable `JSONB`.
- Relationships: `Business.checks` (`lazy="selectin"`, ordered by type) and `VerificationCheck.business`.

## 2. Migration
- `alembic revision --autogenerate -m "initial schema"`, then **edit by hand**:
  - `op.execute("CREATE EXTENSION IF NOT EXISTS citext")` and `pg_trgm` at the top of `upgrade()`. `pgcrypto` isn't needed, because `gen_random_uuid()` is built into PG 13+.
  - GIN trigram indexes: `op.create_index("ix_businesses_name_trgm", "businesses", ["name"], postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"})`, and the same for `director_name`.
  - Partial index: `ix_verification_checks_failed` on `(type)` with `postgresql_where=sa.text("status = 'failed'")`.
  - `downgrade()` drops the tables, then the enum types (autogenerate often forgets enums, so drop them explicitly).
- `make migrate` on an empty DB, then `alembic downgrade base`, then `upgrade head` must all succeed.

## 3. Stage derivation (`app/services/stage.py`)
A pure function with no DB access:
```python
def derive_stage(current: Stage, checks: Mapping[CheckType, CheckStatus], consent_given_at: datetime | None) -> Stage
```
- If `current` is `signed_up` or `documents_submitted`, return `current` unchanged (the console never moves those; see design §5.3).
- If all four checks are `passed`: return `profile_ready` if `consent_given_at` is set, otherwise `bank_linked`.
- Otherwise return `checks_in_progress`.
- Unit-test every combination: 3⁴ check states × consent yes/no × each starting stage.

## 4. Error handling (`app/core/errors.py`)
- `class AppError(Exception)` with `status_code`, `code`, `message` and optional `details`. Add subclasses or factory helpers for every code in design §6.5: `invalid_credentials`, `not_authenticated`, `token_expired`, `forbidden`, `not_found`, `validation_error`, `internal_error` (later phases add the rest).
- Register handlers in `create_app()`:
  - `AppError` → envelope
  - `RequestValidationError` → 422 `validation_error`, with `details: [{"field": "body.email", "message": "…"}]`
  - `StarletteHTTPException` → 404 `not_found`, 405 `method_not_allowed`, anything else → `http_error`
  - bare `Exception` → 500 `internal_error`, logged with traceback, generic message only
- **Request ID middleware:** read `X-Request-ID` or generate `uuid4().hex`, keep it in a `contextvar`, echo it in the response header, and include it in every envelope as `request_id`.
- **Logging** (`app/core/logging.py`): JSON lines to stdout with `ts`, `level`, `msg`, `request_id`, plus an access log per request (`method`, `path`, `status`, `duration_ms`, `actor_id` when known). Never log request bodies or headers.

## 5. Security (`app/core/security.py`)
- `hash_password(pw) -> str` and `verify_password(pw, hash) -> bool` using `bcrypt` directly (cost 12). Don't use passlib, it's unmaintained.
- `DUMMY_HASH`: computed once at import, used to equalise timing when the email doesn't exist.
- `create_access_token(user) -> (token, expires_at)`: HS256 with claims `sub` (user id), `role`, `iat`, `exp` (now + `jwt_ttl_minutes`) and `jti`.
- `get_current_user`: uses `HTTPBearer(auto_error=False)`. **Gotcha:** FastAPI's default returns 403 when the header is missing. We need **401 `not_authenticated`**. On `jwt.ExpiredSignatureError` raise 401 `token_expired`, on any other decode error 401 `not_authenticated`. Load the user by `sub` from the DB (401 if missing) and attach it to `request.state.actor_id` for logging.
- `require_roles(*roles: Role, action: str = "access this resource")` returns a dependency that raises 403 `forbidden` with the message `f"Your role ({role.value.replace('_', ' ')}) cannot {action}."`.

## 6. Audit (`app/services/audit.py`)
`write_audit(db, *, actor_id: UUID | None, action: str, target_type: str, target_id: str | None, details: dict) -> None` adds a row but **doesn't commit** (the caller owns the transaction). Action names in use: `login.success`, `login.failure` (later phases add `check.retry`, `provider.simulate` and `businesses.export`).

## 7. Endpoints (`app/api/v1/routers/auth.py`, mounted at `/api/v1`)
| Endpoint | Request | 200 response | Errors |
|---|---|---|---|
| `POST /auth/login` | `{"email": EmailStr, "password": str (1–128)}` | `{"access_token", "token_type": "bearer", "expires_at", "user": {"id","email","full_name","role"}}` | 401 `invalid_credentials` with the message "Email or password is incorrect." (the same for an unknown email and a wrong password), 422 |
| `GET /auth/me` | Bearer | `{"id","email","full_name","role"}` | 401 |

- Login writes `login.success` (with `actor_id`) or `login.failure` (`actor_id=None`, `details={"email": <lower-cased>}`) and commits.
- Add `email-validator` (or `pydantic[email]`) to the dependencies.
- Use Pydantic response models (`app/schemas/auth.py`) so OpenAPI is accurate. Phase 5 generates TS types from it.

## 8. Seed (`scripts/seed.py`, run with `python -m scripts.seed [--reset]`)
**Structure:** `def run_seed(db: Session, *, now: datetime, reset: bool = False) -> SeedSummary`. It doesn't commit, so tests can call it inside a rolled-back transaction. The `__main__` block opens a session, calls it, commits, and prints the summary.

**Deterministic:** `rng = random.Random(42)` and a fixed "now" taken at seed start. Without `--reset`, exit early with a message if `staff_users` already has rows. `--reset` truncates every table (`TRUNCATE … RESTART IDENTITY CASCADE`).

Keep the name lists in `scripts/seed_data.py` as plain Python lists. **Don't use Faker**: it has no Nigerian locale, and its names would look wrong.

**Staff (15 total):**
| Email | Password | Name | Role |
|---|---|---|---|
| `admin@credisure.demo` | `Admin@2026` | Adaeze Okafor | ops_admin |
| `analyst@credisure.demo` | `Analyst@2026` | Tunde Bakare | analyst |
| `viewer@credisure.demo` | `Viewer@2026` | Hauwa Musa | viewer |
| 12 more `firstname.lastname@credisure.demo` | random, not published | Nigerian names | roughly 4 ops_admin, 6 analyst, 2 viewer |

`created_at` for staff is spread over the last 18 months.

**Businesses (300):**
- **Names:** combine `{prefix} {sector word} {suffix}`. Prefix is a Nigerian surname or word (Adebayo, Chukwu, Danjuma, Okonkwo, Eko, Arewa, Naija, Zuma…). The sector word fits the sector (Agro, Farms, Foods; Stores, Mart; Logistics, Haulage; Tech, Digital; Pharma, Clinics; Hotels, Suites; Builders, Construction; Fabrics, Couture; Academy, Schools). Suffix is one of `Ltd`, `Nigeria Ltd`, `Enterprises`, `Ventures`, `Global Services Ltd`. Names must be unique.
- **Director:** first name + surname drawn from Yoruba, Igbo, Hausa, Edo and Ijaw lists (at least 40 first names and 40 surnames).
- **`cac_number`:** `RC` + 6–7 digits, unique. **`tin`:** `NNNNNNNN-0001`.
- **`state`:** weighted toward Lagos (30%), FCT (12%), Rivers, Oyo, Kano, Kaduna, Anambra, Enugu, Ogun and Delta, with the rest spread across the other states. All 37 must be valid names.
- **`bank_name`:** Access Bank, GTBank, Zenith Bank, First Bank, UBA, Moniepoint, Kuda, Wema Bank, Fidelity Bank, Stanbic IBTC, Sterling Bank, Providus Bank. `bvn_last4` and `account_last4` are random 4-digit strings.
- **`created_at`:** over the last 120 days, weighted toward recent weeks so the sign-ups chart trends up.
- **Stage mix:** signed_up 10%, documents_submitted 12%, checks_in_progress 38%, bank_linked 15%, profile_ready 25%.
- **Checks (exactly 4 per business), consistent with the stage:**
  - `signed_up` / `documents_submitted`: all `pending`, attempts 0, credit_score NULL, no bank sync, no consent.
  - `checks_in_progress`: at least one check is not passed. About 55% have at least one `failed` check. Failures are weighted bvn > bank_link > cac > tin, and some businesses have two. Failed checks have `attempts` 1–3 and a reason chosen per type:
    - cac: "CAC number not found in registry", "Company name does not match CAC record", "Company status is inactive"
    - tin: "TIN not registered with FIRS", "TIN does not match company name"
    - bvn: "BVN name does not match director", "BVN date of birth mismatch", "BVN record not found"
    - bank_link: "Account name does not match company name", "Bank consent expired", "Statement fetch timed out"
  - `bank_linked`: all 4 passed, consent NULL. `profile_ready`: all 4 passed, consent set after the bank link.
  - Passed checks have attempts of 1 or 2. `updated_at` falls between `created_at` and now.
- **`credit_score`:** for stages at `checks_in_progress` and later, use `clamp(round(gauss(640, 70)), 300, 850)`. Skew profile_ready slightly higher (mean 680).
- **`last_bank_sync_at`:** set only when bank_link passed. About 20% of those are **older than 7 days** (the stale-data demo). The rest fall within the last 3 days.
- **Self-check:** before committing, assert that `derive_stage(...) == stage` for every business at `checks_in_progress` or later, and exit non-zero with a message if it fails.
- Print a summary: counts per stage, failed checks per type, and stale bank count.
- `provider_pings` stays empty. Phase 4 extends the seed.

**Startup script:** update `scripts/start.sh` to run `alembic upgrade head`, then `python -m scripts.seed`, then `uvicorn`. The seed's early exit makes restarts safe.

## 9. Tests
**Infrastructure** (`tests/conftest.py`):
- Session scope: drop and recreate `public` on `credisure_test`, then run `alembic upgrade head` programmatically (`alembic.command.upgrade(cfg, "head")`).
- Function scope `db`: one connection with `begin()`, then `Session(bind=conn, join_transaction_mode="create_savepoint")`, rolled back after the test. Override `get_db` with it.
- `tests/factories.py`: `make_staff(db, role=…, password=…)`, `make_business(db, stage=…, checks={…}, **overrides)`, and `auth_header(client, email, password)`.

**Tests:**
- `test_stage.py`: the exhaustive `derive_stage` matrix.
- `test_auth.py`: login success (token decodes, has `role`, and `exp` is about 60 min away); wrong password and unknown email give the same 401 and message; invalid email and empty password give 422 `validation_error` with field details; `/auth/me` with no header, a garbage token, or an expired token (create one with a negative TTL) gives 401 with `not_authenticated` / `token_expired`; a valid token gives 200; login success and failure each write the right audit row.
- `test_errors.py`: unknown route gives 404 envelope; the `X-Request-ID` header is echoed; an unhandled exception (a test-only route) gives a 500 envelope with no traceback in the body.
- `test_roles.py`: mount a test-only route with `require_roles(Role.ops_admin, action="re-run checks")`. A viewer gets 403 with the message "Your role (viewer) cannot re-run checks.", and an ops_admin gets 200.
- `test_seed.py` (marked `slow`, still run by default): run the seed against an empty test schema in a transaction, then assert 300 businesses, 1,200 checks, 15 staff, all stages present, and at least 20 stale bank syncs.

## Acceptance criteria
1. A fresh `docker compose up --build` migrates, seeds, and serves the API. A restart doesn't re-seed.
2. `curl -X POST localhost:8000/api/v1/auth/login -H 'content-type: application/json' -d '{"email":"admin@credisure.demo","password":"Admin@2026"}'` returns a token. Using it on `/api/v1/auth/me` returns the admin.
3. A wrong password returns 401 `{"error":{"code":"invalid_credentials",…,"request_id":…}}`.
4. Every error response anywhere matches the envelope (§6.5).
5. `alembic downgrade base && alembic upgrade head` succeeds.
6. Running the seed twice gives the same data (same CAC numbers, the same 10 business names in the same order).
7. `make lint` and `make test` pass, with coverage at least 85% on `app/core` and `app/services`.
8. `/docs` shows the login and me endpoints with correct schemas.

## Verify
```bash
make db && make migrate && cd api && uv run alembic downgrade base && uv run alembic upgrade head && cd ..
make seed
make lint && make test
docker compose up --build -d && sleep 20
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -H 'content-type: application/json' -d '{"email":"admin@credisure.demo","password":"Admin@2026"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"
curl -s -X POST localhost:8000/api/v1/auth/login -H 'content-type: application/json' -d '{"email":"admin@credisure.demo","password":"nope"}'
curl -s localhost:8000/api/v1/auth/me
docker compose exec db psql -U credisure -c "select stage, count(*) from businesses group by 1 order by 1;"
```

## Out of scope
Business, stats and provider endpoints (Phases 3–4). Rate limiting (future work).

## Review checklist (Opus)
- [ ] There is no code path that stores or logs a full BVN or account number (ADR-006).
- [ ] Unknown-email login still runs bcrypt (DUMMY_HASH), so timing is equal.
- [ ] A missing bearer gives **401**, not FastAPI's default 403.
- [ ] The role comes from the DB user, not the token claim.
- [ ] The migration creates the extensions, the trigram and partial indexes, and the named constraints, and its downgrade drops the enum types.
- [ ] The seed is deterministic and its self-check runs. Stage and check consistency holds.
- [ ] The test DB isolation really rolls back (no data leaking between tests).
- [ ] The 500 handler hides internals and still logs the traceback with `request_id`.
