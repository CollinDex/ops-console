import asyncio
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProviderPing
from app.models.enums import PingStatus, ProviderName
from app.providers.base import PingResult
from app.providers.pinger import ping_once, run_pinger
from app.providers.registry import ProviderRegistry
from app.providers.simulator import SimulatedProvider
from tests.conftest import SharedSession, fast_sleep


class _ExplodingProvider(SimulatedProvider):
    async def ping(self) -> PingResult:
        raise RuntimeError("boom")


def _registry(exploding: ProviderName | None = None) -> ProviderRegistry:
    providers = [
        (_ExplodingProvider if n == exploding else SimulatedProvider)(
            n, random.Random(3), sleep=fast_sleep
        )
        for n in ProviderName
    ]
    return ProviderRegistry(providers)


async def _run_for(registry: ProviderRegistry, factory: object, seconds: float) -> None:
    stop = asyncio.Event()
    task = asyncio.create_task(
        run_pinger(registry, factory, stop=stop, interval=0.01)  # type: ignore[arg-type]
    )
    await asyncio.sleep(seconds)
    stop.set()
    await asyncio.wait_for(task, 2)


def test_pinger_writes_rows_and_records_down(db: Session) -> None:
    registry = _registry()
    registry.get(ProviderName.cac).set_mode("down")
    asyncio.run(_run_for(registry, SharedSession(db), 0.15))
    rows = db.scalars(select(ProviderPing)).all()
    assert len(rows) >= 8 and len(rows) % 4 == 0
    down = [r for r in rows if r.provider == ProviderName.cac]
    assert down and all(r.status == PingStatus.down and r.error for r in down)
    assert {r.provider for r in rows} == set(ProviderName)


def test_pinger_survives_a_provider_that_raises(db: Session) -> None:
    registry = _registry(exploding=ProviderName.tin)
    asyncio.run(_run_for(registry, SharedSession(db), 0.15))
    tin = db.scalars(select(ProviderPing).where(ProviderPing.provider == ProviderName.tin)).all()
    assert len(tin) >= 2  # kept looping
    assert all(r.status == PingStatus.down and r.error == "boom" for r in tin)


def test_pinger_survives_a_failing_iteration(db: Session) -> None:
    calls = {"n": 0}

    def flaky_factory() -> SharedSession:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise RuntimeError("db is restarting")
        return SharedSession(db)

    asyncio.run(_run_for(_registry(), flaky_factory, 0.2))
    assert calls["n"] > 2
    assert db.scalars(select(ProviderPing)).first() is not None


def test_ping_once_subset(db: Session) -> None:
    asyncio.run(ping_once(_registry(), SharedSession(db), [ProviderName.bvn]))  # type: ignore[arg-type]
    rows = db.scalars(select(ProviderPing)).all()
    assert [r.provider for r in rows] == [ProviderName.bvn]
