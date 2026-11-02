"""Provider status, uptime and incident grouping (design sections 6.1, 7.4, 9)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.models import ProviderPing
from app.models.enums import PingStatus, ProviderName
from app.providers.registry import ProviderRegistry
from app.schemas.providers import (
    IncidentOut,
    PingPointOut,
    ProvidersStatusOut,
    ProviderStatusOut,
    ProviderSummary,
)
from app.services.catalog import PROVIDER_LABELS

RECENT_PINGS = 40
INCIDENT_WINDOW = timedelta(days=7)
INCIDENT_LIMIT = 20


@dataclass(frozen=True)
class PingPoint:
    checked_at: datetime
    status: PingStatus


@dataclass(frozen=True)
class Incident:
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int
    worst_status: Literal["down", "slow"]
    ping_count: int


def group_incidents(pings: Sequence[PingPoint], now: datetime | None = None) -> list[Incident]:
    """Group consecutive non-up pings (given oldest first) into incidents, oldest first.

    An incident ends at the first `up` ping after it. A run that reaches the end of the
    input is ongoing: `ended_at` is None and the duration runs up to `now`.
    """
    now = now or datetime.now(UTC)
    incidents: list[Incident] = []
    run: list[PingPoint] = []

    def close(ended_at: datetime | None) -> None:
        if not run:
            return
        end = ended_at or now
        worst: Literal["down", "slow"] = (
            "down" if any(p.status == PingStatus.down for p in run) else "slow"
        )
        incidents.append(
            Incident(
                started_at=run[0].checked_at,
                ended_at=ended_at,
                duration_seconds=max(0, int((end - run[0].checked_at).total_seconds())),
                worst_status=worst,
                ping_count=len(run),
            )
        )
        run.clear()

    for ping in pings:
        if ping.status == PingStatus.up:
            close(ping.checked_at)
        else:
            run.append(ping)
    close(None)
    return incidents


def latest_pings(db: Session) -> dict[ProviderName, ProviderPing]:
    rows = db.scalars(
        select(ProviderPing)
        .ext(distinct_on(ProviderPing.provider))
        .order_by(ProviderPing.provider, ProviderPing.checked_at.desc())
    ).all()
    return {r.provider: r for r in rows}


def ping_summary(db: Session) -> ProviderSummary:
    counts = {"up": 0, "slow": 0, "down": 0}
    for ping in latest_pings(db).values():
        counts[ping.status.value] += 1
    return ProviderSummary(**counts)


def _recent(db: Session) -> dict[ProviderName, list[ProviderPing]]:
    ranked = (
        select(
            ProviderPing.id,
            func.row_number()
            .over(partition_by=ProviderPing.provider, order_by=ProviderPing.checked_at.desc())
            .label("rn"),
        )
    ).subquery()
    rows = db.scalars(
        select(ProviderPing)
        .join(ranked, ranked.c.id == ProviderPing.id)
        .where(ranked.c.rn <= RECENT_PINGS)
        .order_by(ProviderPing.checked_at)
    ).all()
    out: dict[ProviderName, list[ProviderPing]] = {}
    for row in rows:
        out.setdefault(row.provider, []).append(row)
    return out


def provider_statuses(
    db: Session, registry: ProviderRegistry, names: Sequence[ProviderName] | None = None
) -> ProvidersStatusOut:
    now = datetime.now(UTC)
    wanted = list(names) if names is not None else list(ProviderName)
    latest = latest_pings(db)
    recent = _recent(db)
    stats = {
        row.provider: row
        for row in db.execute(
            select(
                ProviderPing.provider,
                func.count().label("total"),
                func.count().filter(ProviderPing.status != PingStatus.down).label("ok"),
                func.avg(ProviderPing.latency_ms).filter(ProviderPing.latency_ms.is_not(None)),
            )
            .where(ProviderPing.checked_at >= now - timedelta(hours=24))
            .group_by(ProviderPing.provider)
        )
    }
    providers: list[ProviderStatusOut] = []
    summary = {"up": 0, "slow": 0, "down": 0}
    for name in wanted:
        ping = latest.get(name)
        stat = stats.get(name)
        status = ping.status.value if ping else "unknown"
        if ping:
            summary[status] += 1
        providers.append(
            ProviderStatusOut(
                name=name,
                label=PROVIDER_LABELS[name],
                status=cast(Literal["up", "slow", "down", "unknown"], status),
                mode=registry.get(name).mode,
                latency_ms=ping.latency_ms if ping else None,
                last_checked_at=ping.checked_at if ping else None,
                uptime_24h=round(100 * stat.ok / stat.total, 1) if stat and stat.total else None,
                avg_latency_24h=round(stat[3]) if stat and stat[3] is not None else None,
                recent=[
                    PingPointOut(
                        checked_at=p.checked_at,
                        status=p.status.value,
                        latency_ms=p.latency_ms,
                    )
                    for p in recent.get(name, [])
                ],
            )
        )
    return ProvidersStatusOut(
        providers=providers, summary=ProviderSummary(**summary), generated_at=now
    )


def incidents_for(db: Session, name: ProviderName) -> list[IncidentOut]:
    now = datetime.now(UTC)
    rows = db.execute(
        select(ProviderPing.checked_at, ProviderPing.status)
        .where(ProviderPing.provider == name, ProviderPing.checked_at >= now - INCIDENT_WINDOW)
        .order_by(ProviderPing.checked_at)
    ).all()
    incidents = group_incidents([PingPoint(r.checked_at, r.status) for r in rows], now)
    incidents.reverse()
    return [
        IncidentOut(
            started_at=i.started_at,
            ended_at=i.ended_at,
            duration_seconds=i.duration_seconds,
            worst_status=i.worst_status,
            ping_count=i.ping_count,
        )
        for i in incidents[:INCIDENT_LIMIT]
    ]
