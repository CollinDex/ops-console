"""VerificationProvider protocol, PingResult and CheckResult (design section 4.1)."""

import uuid
from dataclasses import dataclass
from typing import Protocol

from app.models.enums import CheckType, PingStatus, ProviderName

SLOW_THRESHOLD_MS = 1000
CALL_TIMEOUT_S = 5.0

CHECK_PROVIDER: dict[CheckType, ProviderName] = {
    CheckType.cac: ProviderName.cac,
    CheckType.tin: ProviderName.tin,
    CheckType.bvn: ProviderName.bvn,
    CheckType.bank_link: ProviderName.open_banking,
}


class ProviderUnavailable(Exception):  # noqa: N818 - domain name used across the design docs
    def __init__(self, name: ProviderName) -> None:
        super().__init__(f"Provider unavailable ({name.value})")
        self.provider = name


@dataclass(frozen=True)
class PingResult:
    status: PingStatus
    latency_ms: int | None
    error: str | None


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    failure_reason: str | None


class VerificationProvider(Protocol):
    name: ProviderName

    async def ping(self) -> PingResult: ...

    async def verify(self, business_id: uuid.UUID, check: CheckType) -> CheckResult: ...
