import asyncio
import random
import uuid

import pytest

from app.models.enums import CheckType, PingStatus, ProviderName
from app.providers.base import SLOW_THRESHOLD_MS, ProviderUnavailable
from app.providers.simulator import SimulatedProvider
from app.services.catalog import FAILURE_REASONS


def _provider(pass_rate: float = 0.8) -> tuple[SimulatedProvider, list[float]]:
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    return (
        SimulatedProvider(ProviderName.bvn, random.Random(7), sleep=record, pass_rate=pass_rate),
        slept,
    )


def test_up_latency_range_and_status() -> None:
    provider, _ = _provider()
    results = [asyncio.run(provider.ping()) for _ in range(50)]
    assert all(r.status == PingStatus.up and r.error is None for r in results)
    assert all(r.latency_ms is not None and 80 <= r.latency_ms <= 250 for r in results)


def test_slow_latency_range_and_status() -> None:
    provider, _ = _provider()
    provider.set_mode("slow")
    results = [asyncio.run(provider.ping()) for _ in range(50)]
    assert all(r.status == PingStatus.slow for r in results)
    assert all(r.latency_ms is not None and 1200 <= r.latency_ms <= 2500 for r in results)
    assert all(r.latency_ms >= SLOW_THRESHOLD_MS for r in results if r.latency_ms)


def test_down_ping_and_verify() -> None:
    provider, slept = _provider()
    provider.set_mode("down")
    ping = asyncio.run(provider.ping())
    assert (ping.status, ping.latency_ms) == (PingStatus.down, None)
    assert ping.error == "Connection refused (simulated)"
    with pytest.raises(ProviderUnavailable):
        asyncio.run(provider.verify(uuid.uuid4(), CheckType.bvn))
    assert slept == [0.3, 0.3]


def test_verify_counts_calls_and_uses_catalog_reasons() -> None:
    provider, _ = _provider(pass_rate=0.0)
    for _ in range(5):
        result = asyncio.run(provider.verify(uuid.uuid4(), CheckType.bvn))
        assert not result.passed
        assert result.failure_reason in FAILURE_REASONS[CheckType.bvn]
    assert provider.verify_calls == 5


def test_verify_passes_when_pass_rate_is_one() -> None:
    provider, _ = _provider(pass_rate=1.0)
    result = asyncio.run(provider.verify(uuid.uuid4(), CheckType.bvn))
    assert result.passed and result.failure_reason is None
