from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import VerificationCheck
from app.models.enums import CheckStatus, CheckType, Stage
from app.services.stats import overview, week_starts
from tests.factories import make_business

URL = "/api/v1/stats/overview"
P, F = CheckStatus.passed, CheckStatus.failed
ALL_PASSED = dict.fromkeys(CheckType, P)


def build_fixture(db: Session, now: datetime) -> dict[str, str]:
    """Ten businesses with known values. Returns name -> id."""
    d = timedelta
    specs = [
        # name, stage, checks, score, created_ago, last_sync_ago
        ("ready1", Stage.profile_ready, ALL_PASSED, 800, d(days=30), d(days=1)),
        ("ready2", Stage.profile_ready, ALL_PASSED, 700, d(days=20), d(days=2)),
        # fully verified, bank_linked, but bank data stale (9 days)
        ("stale", Stage.bank_linked, ALL_PASSED, 650, d(days=15), d(days=9)),
        # failed bvn, new (2 days): stuck via failed check
        (
            "failbvn",
            Stage.checks_in_progress,
            {CheckType.bvn: F, CheckType.cac: P},
            500,
            d(days=2),
            None,
        ),
        # two failed checks, bank_link passed and stale: stuck, two + stale reasons
        (
            "multi",
            Stage.checks_in_progress,
            {CheckType.cac: F, CheckType.tin: F, CheckType.bank_link: P},
            None,
            d(days=12),
            d(days=10),
        ),
        # no failure but older than 7 days: stuck, not needs-attention
        ("slow", Stage.checks_in_progress, {CheckType.cac: P}, 600, d(days=8), None),
        # new and fine: neither
        ("fresh", Stage.checks_in_progress, {CheckType.cac: P}, 550, d(days=1), None),
        # pre-check stages: old signed_up counts as stuck (>7 days)
        ("oldsignup", Stage.signed_up, {}, None, d(days=40), None),
        ("newdocs", Stage.documents_submitted, {}, None, d(days=3), None),
        # stale sync but bank_link NOT passed: not needs-attention
        (
            "notpassed",
            Stage.checks_in_progress,
            {CheckType.bank_link: CheckStatus.pending},
            450,
            d(days=2),
            d(days=20),
        ),
    ]
    ids = {}
    for name, stage, checks, score, created_ago, sync_ago in specs:
        b = make_business(
            db,
            name=name,
            stage=stage,
            checks=checks,
            credit_score=score,
            created_at=now - created_ago,
            last_bank_sync_at=None if sync_ago is None else now - sync_ago,
        )
        ids[name] = str(b.id)
    return ids


def set_failed_at(db: Session, business_id: str, check_type: CheckType, when: datetime) -> None:
    db.execute(
        update(VerificationCheck)
        .where(VerificationCheck.business_id == business_id, VerificationCheck.type == check_type)
        .values(updated_at=when)
    )


def test_overview_numbers(db: Session) -> None:
    now = datetime.now(UTC)
    ids = build_fixture(db, now)
    set_failed_at(db, ids["failbvn"], CheckType.bvn, now - timedelta(hours=5))
    set_failed_at(db, ids["multi"], CheckType.cac, now - timedelta(days=1))
    set_failed_at(db, ids["multi"], CheckType.tin, now - timedelta(days=2))

    out = overview(db, now)

    c = out.cards
    assert c.total_businesses == 10
    assert c.fully_verified == 3  # ready1, ready2, stale
    # stuck: failbvn, multi, slow, oldsignup, stale (15 days old)
    assert c.stuck == 5
    scores = [800, 700, 650, 500, 600, 550, 450]
    assert c.avg_credit_score == round(sum(scores) / len(scores), 1)

    assert [(f.stage.value, f.count) for f in out.funnel] == [
        ("signed_up", 1),
        ("documents_submitted", 1),
        ("checks_in_progress", 5),
        ("bank_linked", 1),
        ("profile_ready", 2),
    ]
    assert out.funnel[0].label == "Signed up"

    attention = out.needs_attention
    # since: failbvn 5h ago, multi 1 day ago (newest failed), stale -> last sync 9 days ago.
    assert [a.name for a in attention] == ["failbvn", "multi", "stale"]
    assert [r.label for r in attention[0].reasons] == ["BVN failed"]
    assert [r.label for r in attention[1].reasons] == [
        "CAC failed",
        "Tax ID failed",
        "Bank data 10 days old",
    ]
    assert attention[1].reasons[2].kind == "stale_bank_data" and attention[1].reasons[2].days == 10
    assert attention[1].reasons[0].kind == "failed_check"
    assert attention[1].reasons[0].check == CheckType.cac
    assert [r.label for r in attention[2].reasons] == ["Bank data 9 days old"]
    assert attention[2].since == now - timedelta(days=9)

    starts = week_starts(now)
    assert len(out.signups) == 12 and [s.week_start for s in out.signups] == starts
    assert all(s.week_start.weekday() == 0 for s in out.signups)
    assert sum(s.count for s in out.signups) == 10  # all ten were created within 12 weeks


def test_needs_attention_limit_and_order(db: Session) -> None:
    now = datetime.now(UTC)
    for i in range(12):
        b = make_business(db, checks={CheckType.cac: F})
        set_failed_at(db, str(b.id), CheckType.cac, now - timedelta(hours=i + 1))
    out = overview(db, now)
    assert len(out.needs_attention) == 10
    sinces = [a.since for a in out.needs_attention]
    assert sinces == sorted(sinces, reverse=True)


def test_empty_database(db: Session) -> None:
    out = overview(db)
    assert out.cards.total_businesses == 0 and out.cards.avg_credit_score is None
    assert [f.count for f in out.funnel] == [0] * 5
    assert out.needs_attention == [] and [s.count for s in out.signups] == [0] * 12


def test_week_boundaries_use_lagos_time() -> None:
    # Sunday 23:30 UTC is already Monday 00:30 in Lagos (UTC+1).
    now = datetime(2026, 11, 1, 23, 30, tzinfo=UTC)  # Sunday
    assert week_starts(now)[-1].isoformat() == "2026-11-02"
    assert week_starts(now)[0].isoformat() == "2026-08-17"


def test_signup_in_lagos_week(db: Session) -> None:
    now = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)  # Wednesday
    # Sunday 23:30 UTC 1 Nov = Monday 00:30 Lagos 2 Nov: belongs to the week of 2 Nov.
    make_business(db, created_at=datetime(2026, 11, 1, 23, 30, tzinfo=UTC))
    make_business(db, created_at=datetime(2026, 11, 1, 22, 30, tzinfo=UTC))  # week of 26 Oct
    out = overview(db, now)
    counts = {s.week_start.isoformat(): s.count for s in out.signups}
    assert counts["2026-11-02"] == 1 and counts["2026-10-26"] == 1


def test_endpoint_open_to_all_roles(client: TestClient, viewer_headers: dict[str, str]) -> None:
    resp = client.get(URL, headers=viewer_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"cards", "funnel", "needs_attention", "signups", "generated_at"}
    assert "director" not in resp.text
    assert client.get(URL).status_code == 401
