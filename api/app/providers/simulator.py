"""SimulatedProvider with modes up, slow and down (design section 7.4)."""

import asyncio
import random
import threading
import uuid
from collections.abc import Awaitable, Callable
from typing import Literal

from app.models.enums import CheckType, PingStatus, ProviderName
from app.providers.base import SLOW_THRESHOLD_MS, CheckResult, PingResult, ProviderUnavailable
from app.services.catalog import FAILURE_REASONS

Mode = Literal["up", "slow", "down"]

UP_LATENCY_MS = (80, 250)
SLOW_LATENCY_MS = (1200, 2500)
DOWN_DELAY_S = 0.3


class SimulatedProvider:
    def __init__(
        self,
        name: ProviderName,
        rng: random.Random,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        pass_rate: float = 0.8,
    ) -> None:
        self.name = name
        self.rng = rng
        self.sleep = sleep
        self.pass_rate = pass_rate
        self.verify_calls = 0
        self._mode: Mode = "up"
        self._lock = threading.Lock()

    @property
    def mode(self) -> Mode:
        with self._lock:
            return self._mode

    def set_mode(self, mode: Mode) -> None:
        with self._lock:
            self._mode = mode

    def _latency_ms(self, mode: Mode) -> int:
        low, high = SLOW_LATENCY_MS if mode == "slow" else UP_LATENCY_MS
        return round(self.rng.uniform(low, high))

    async def ping(self) -> PingResult:
        mode = self.mode
        if mode == "down":
            await self.sleep(DOWN_DELAY_S)
            return PingResult(PingStatus.down, None, "Connection refused (simulated)")
        latency = self._latency_ms(mode)
        await self.sleep(latency / 1000)
        status = PingStatus.slow if latency >= SLOW_THRESHOLD_MS else PingStatus.up
        return PingResult(status, latency, None)

    async def verify(self, business_id: uuid.UUID, check: CheckType) -> CheckResult:
        self.verify_calls += 1
        mode = self.mode
        if mode == "down":
            await self.sleep(DOWN_DELAY_S)
            raise ProviderUnavailable(self.name)
        await self.sleep(self._latency_ms(mode) / 1000)
        if self.rng.random() < self.pass_rate:
            return CheckResult(True, None)
        return CheckResult(False, self.rng.choice(FAILURE_REASONS[check]))
