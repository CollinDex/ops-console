"""Deterministic seed: 15 staff, 300 businesses, 1,200 checks.

Usage: python -m scripts.seed [--reset]
Without --reset the script exits early when staff already exist, so restarts are safe.
"""

import random
import sys
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.models import AuditLog, Business, ProviderPing, StaffUser, VerificationCheck
from app.models.enums import CheckStatus, CheckType, PingStatus, ProviderName, Role, Sector, Stage
from app.services.catalog import FAILURE_REASONS
from app.services.stage import derive_stage
from scripts.seed_data import (
    ALL_STATES,
    BANKS,
    EXTRA_STAFF,
    FAILURE_WEIGHTS,
    FIRST_NAMES,
    HEAVY_STATES,
    NAME_PREFIXES,
    NAME_SUFFIXES,
    SECTOR_WORDS,
    SURNAMES,
)

SEED = 42
STAGE_COUNTS: dict[Stage, int] = {
    Stage.signed_up: 30,  # 10%
    Stage.documents_submitted: 36,  # 12%
    Stage.checks_in_progress: 114,  # 38%
    Stage.bank_linked: 45,  # 15%
    Stage.profile_ready: 75,  # 25%
}
DEMO_STAFF = [
    ("admin@credisure.demo", "Admin@2026", "Adaeze Okafor", Role.ops_admin),
    ("analyst@credisure.demo", "Analyst@2026", "Tunde Bakare", Role.analyst),
    ("viewer@credisure.demo", "Viewer@2026", "Hauwa Musa", Role.viewer),
]


class SeedError(Exception):
    pass


@dataclass
class SeedSummary:
    staff: int = 0
    businesses: int = 0
    checks: int = 0
    stages: Counter[str] = field(default_factory=Counter)
    failed_by_type: Counter[str] = field(default_factory=Counter)
    stale_bank: int = 0
    pings: int = 0
    retry_audit: int = 0

    def render(self) -> str:
        lines = [
            f"staff: {self.staff}  businesses: {self.businesses}  checks: {self.checks}",
            "stages: " + ", ".join(f"{k}={v}" for k, v in self.stages.items()),
            "failed checks: "
            + ", ".join(f"{k}={v}" for k, v in sorted(self.failed_by_type.items())),
            f"stale bank syncs (>7 days): {self.stale_bank}",
            f"provider pings: {self.pings}  retry audit rows: {self.retry_audit}",
        ]
        return "\n".join(lines)


def _uuid(rng: random.Random) -> uuid.UUID:
    return uuid.UUID(int=rng.getrandbits(128), version=4)


def _seed_staff(db: Session, rng: random.Random, now: datetime) -> list[StaffUser]:
    rows: list[tuple[str, str, str, Role]] = list(DEMO_STAFF)
    for first, last, role in EXTRA_STAFF:
        email = f"{first}.{last}@credisure.demo".lower()
        password = "".join(rng.choices("abcdefghijkmnpqrstuvwxyz23456789", k=16))
        rows.append((email, password, f"{first} {last}", Role(role)))
    users = [
        StaffUser(
            id=_uuid(rng),
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            created_at=now - timedelta(days=rng.uniform(1, 18 * 30)),
        )
        for email, password, full_name, role in rows
    ]
    db.add_all(users)
    return users


def _pick_failed(rng: random.Random) -> set[CheckType]:
    count = 2 if rng.random() < 0.2 else 1
    pool = dict(FAILURE_WEIGHTS)
    chosen: set[CheckType] = set()
    for _ in range(count):
        pick = rng.choices(list(pool), weights=list(pool.values()))[0]
        chosen.add(pick)
        del pool[pick]
    return chosen


def _check_statuses(rng: random.Random, stage: Stage) -> dict[CheckType, CheckStatus]:
    types = list(CheckType)
    if stage in (Stage.signed_up, Stage.documents_submitted):
        return dict.fromkeys(types, CheckStatus.pending)
    if stage in (Stage.bank_linked, Stage.profile_ready):
        return dict.fromkeys(types, CheckStatus.passed)
    # checks_in_progress: at least one check is not passed.
    if rng.random() < 0.55:
        failed = _pick_failed(rng)
        return {
            t: CheckStatus.failed
            if t in failed
            else (CheckStatus.passed if rng.random() < 0.6 else CheckStatus.pending)
            for t in types
        }
    statuses = {
        t: (CheckStatus.pending if rng.random() < 0.5 else CheckStatus.passed) for t in types
    }
    if all(s == CheckStatus.passed for s in statuses.values()):
        statuses[rng.choice(types)] = CheckStatus.pending
    return statuses


def _business_name(rng: random.Random, sector: Sector, used: set[str]) -> str:
    while True:
        name = (
            f"{rng.choice(NAME_PREFIXES)} {rng.choice(SECTOR_WORDS[sector])} "
            f"{rng.choice(NAME_SUFFIXES)}"
        )
        if name not in used:
            used.add(name)
            return name


def _unique_digits(
    rng: random.Random, used: set[str], prefix: str, lengths: tuple[int, ...]
) -> str:
    while True:
        n = rng.choice(lengths)
        value = prefix + "".join(rng.choices("0123456789", k=n))
        if value not in used:
            used.add(value)
            return value


# (minimum days, extra span, skew exponent): higher skew keeps more businesses near the minimum.
STAGE_AGE_DAYS: dict[Stage, tuple[float, float, float]] = {
    Stage.signed_up: (0, 10, 2.0),
    Stage.documents_submitted: (0, 12, 2.0),
    Stage.checks_in_progress: (1, 20, 1.5),
    Stage.bank_linked: (1, 20, 2.0),
    Stage.profile_ready: (10, 110, 1.3),
}


def _seed_businesses(db: Session, rng: random.Random, now: datetime, summary: SeedSummary) -> None:
    stages = [s for s, n in STAGE_COUNTS.items() for _ in range(n)]
    rng.shuffle(stages)

    used_names: set[str] = set()
    used_cac: set[str] = set()
    state_weights = [HEAVY_STATES.get(s, 1) for s in ALL_STATES]
    sectors = list(Sector)
    stale_cutoff = now - timedelta(days=7)

    for stage in stages:
        # Age depends on stage: a business that signed up months ago has usually moved on,
        # so early stages are recent and profile-ready ones are older.
        base, span, skew = STAGE_AGE_DAYS[stage]
        created_at = now - timedelta(
            days=base + span * rng.random() ** skew, seconds=rng.randint(0, 86399)
        )
        created_at = min(created_at, now - timedelta(hours=1))
        sector = rng.choice(sectors)
        statuses = _check_statuses(rng, stage)
        passed_bank = statuses[CheckType.bank_link] == CheckStatus.passed

        last_sync: datetime | None = None
        if passed_bank:
            if rng.random() < 0.3 and created_at < now - timedelta(days=8):
                last_sync = now - timedelta(days=rng.uniform(7.5, 30))
                last_sync = max(last_sync, created_at)
            else:
                last_sync = max(created_at, now - timedelta(days=rng.uniform(0, 3)))
            if last_sync < stale_cutoff:
                summary.stale_bank += 1

        consent: datetime | None = None
        if stage == Stage.profile_ready and last_sync is not None:
            consent = min(now, last_sync + timedelta(hours=rng.uniform(0.1, 48)))

        score: int | None = None
        if stage not in (Stage.signed_up, Stage.documents_submitted):
            mean = 680 if stage == Stage.profile_ready else 640
            score = max(300, min(850, round(rng.gauss(mean, 70))))

        business = Business(
            id=_uuid(rng),
            name=_business_name(rng, sector, used_names),
            cac_number=_unique_digits(rng, used_cac, "RC", (6, 7)),
            tin=f"{rng.randint(10_000_000, 99_999_999)}-0001",
            sector=sector,
            state=rng.choices(ALL_STATES, weights=state_weights)[0],
            director_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)}",
            bvn_last4=f"{rng.randint(0, 9999):04d}",
            bank_name=rng.choice(BANKS),
            account_last4=f"{rng.randint(0, 9999):04d}",
            stage=stage,
            credit_score=score,
            consent_given_at=consent,
            last_bank_sync_at=last_sync,
            created_at=created_at,
            updated_at=created_at + (now - created_at) * rng.random(),
        )
        db.add(business)

        for check_type in CheckType:
            status = statuses[check_type]
            if status == CheckStatus.failed:
                attempts = rng.randint(1, 3)
                reason: str | None = rng.choice(FAILURE_REASONS[check_type])
                summary.failed_by_type[check_type.value] += 1
            elif status == CheckStatus.passed:
                attempts, reason = rng.randint(1, 2), None
            else:
                attempts, reason = 0, None
            if status == CheckStatus.pending:
                updated_at = created_at
            elif check_type == CheckType.bank_link and last_sync is not None:
                updated_at = last_sync
            else:
                updated_at = created_at + (now - created_at) * rng.random()
            db.add(
                VerificationCheck(
                    id=_uuid(rng),
                    business_id=business.id,
                    type=check_type,
                    status=status,
                    failure_reason=reason,
                    attempts=attempts,
                    updated_at=updated_at,
                )
            )
            summary.checks += 1

        # Self-check: stored stage must equal the derived stage from checks_in_progress on.
        if stage not in (Stage.signed_up, Stage.documents_submitted):
            derived = derive_stage(stage, statuses, consent)
            if derived != stage:
                raise SeedError(f"stage mismatch for {business.name}: {stage} vs {derived}")
        summary.stages[stage.value] += 1
        summary.businesses += 1


LAGOS = timezone(timedelta(hours=1))  # Africa/Lagos has no DST, so a fixed offset is exact
PING_DAYS = 7
PING_CHUNK = 5000
RETRY_AUDIT_BUSINESSES = 12


def _scripted_outages(now: datetime) -> dict[ProviderName, list[tuple[datetime, int, PingStatus]]]:
    """(start, minutes, status) windows that make the incident history non-empty."""
    yesterday = (now.astimezone(LAGOS) - timedelta(days=1)).replace(
        hour=14, minute=10, second=0, microsecond=0
    )
    return {
        ProviderName.bvn: [(yesterday, 25, PingStatus.down)],
        ProviderName.open_banking: [(now - timedelta(days=3), 120, PingStatus.slow)],
        ProviderName.cac: [(now - timedelta(days=5), 10, PingStatus.down)],
        ProviderName.tin: [
            (now - timedelta(days=2, hours=3), 2, PingStatus.slow),
            (now - timedelta(days=4, hours=7), 2, PingStatus.slow),
        ],
    }


def seed_pings(db: Session, now: datetime, rng: random.Random) -> int:
    """Seven days of 1-minute pings per provider, bulk inserted, with scripted incidents."""
    outages = _scripted_outages(now)
    end = now.replace(second=0, microsecond=0)
    total = PING_DAYS * 24 * 60
    rows: list[dict[str, object]] = []
    for provider in ProviderName:
        windows = [
            (start, start + timedelta(minutes=mins), st) for start, mins, st in outages[provider]
        ]
        for i in range(total):
            checked_at = end - timedelta(minutes=i)
            status = PingStatus.up
            for start, stop, st in windows:
                if start <= checked_at < stop:
                    status = st
            if status == PingStatus.down:
                latency, error = None, "Connection refused (simulated)"
            elif status == PingStatus.slow:
                latency, error = rng.randint(1200, 2500), None
            else:
                latency, error = rng.randint(80, 250), None
            rows.append(
                {
                    "provider": provider,
                    "status": status,
                    "latency_ms": latency,
                    "error": error,
                    "checked_at": checked_at,
                }
            )
    for i in range(0, len(rows), PING_CHUNK):
        db.execute(insert(ProviderPing), rows[i : i + PING_CHUNK])
    return len(rows)


def seed_retry_audit(db: Session, now: datetime, rng: random.Random) -> int:
    """check.retry audit rows from the demo admin for businesses whose checks were re-run."""
    admin = db.scalars(select(StaffUser).where(StaffUser.email == DEMO_STAFF[0][0])).one()
    candidates = db.execute(
        select(Business, VerificationCheck)
        .join(VerificationCheck)
        .where(VerificationCheck.attempts >= 2)
        .order_by(Business.cac_number, VerificationCheck.type)
        .limit(RETRY_AUDIT_BUSINESSES * 3)
    ).all()
    seen: set[uuid.UUID] = set()
    count = 0
    for business, check in candidates:
        if business.id in seen:
            continue
        seen.add(business.id)
        retry_time = min(
            now - timedelta(minutes=5),
            max(business.created_at, now - timedelta(days=6)) + timedelta(hours=rng.randint(1, 48)),
        )
        db.add(
            AuditLog(
                actor_id=admin.id,
                action="check.retry",
                target_type="business",
                target_id=str(business.id),
                details={
                    "check": check.type.value,
                    "result": "passed" if check.status == CheckStatus.passed else "failed",
                    "failure_reason": check.failure_reason,
                    "attempts": check.attempts,
                    "idempotency_key": str(_uuid(rng)),
                },
                created_at=retry_time,
            )
        )
        count += 1
        if count >= RETRY_AUDIT_BUSINESSES:
            break
    return count


def run_seed(db: Session, *, now: datetime, reset: bool = False) -> SeedSummary:
    """Fill the database. Does not commit, so tests can roll it back."""
    if reset:
        tables = ", ".join(
            t.name for t in Base.metadata.sorted_tables if t.name != "alembic_version"
        )
        db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    rng = random.Random(SEED)
    summary = SeedSummary()
    summary.staff = len(_seed_staff(db, rng, now))
    _seed_businesses(db, rng, now, summary)
    db.flush()
    extra_rng = random.Random(SEED + 1)  # separate stream: businesses stay identical to Phase 3
    summary.pings = seed_pings(db, now, extra_rng)
    summary.retry_audit = seed_retry_audit(db, now, extra_rng)
    db.flush()
    return summary


def main(argv: list[str]) -> int:
    from app.db.session import SessionLocal

    reset = "--reset" in argv
    with SessionLocal() as db:
        if not reset and db.scalar(select(func.count()).select_from(StaffUser)):
            print("Seed skipped: staff_users already has rows (use --reset to rebuild).")
            return 0
        try:
            summary = run_seed(db, now=datetime.now().astimezone(), reset=reset)
        except SeedError as exc:
            db.rollback()
            print(f"Seed failed self-check: {exc}", file=sys.stderr)
            return 1
        db.commit()
    print(summary.render())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
