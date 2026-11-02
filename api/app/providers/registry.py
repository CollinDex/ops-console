"""Provider name to instance registry, plus the FastAPI dependency that exposes it."""

import random

from app.models.enums import CheckType, ProviderName
from app.providers.base import CHECK_PROVIDER
from app.providers.simulator import SimulatedProvider


class ProviderRegistry:
    def __init__(self, providers: list[SimulatedProvider]) -> None:
        self._providers = {p.name: p for p in providers}

    def get(self, name: ProviderName) -> SimulatedProvider:
        return self._providers[name]

    def all(self) -> list[SimulatedProvider]:
        return [self._providers[n] for n in ProviderName]

    def for_check(self, check_type: CheckType) -> SimulatedProvider:
        return self.get(CHECK_PROVIDER[check_type])


def build_registry(rng: random.Random | None = None) -> ProviderRegistry:
    return ProviderRegistry([SimulatedProvider(n, rng or random.Random()) for n in ProviderName])


registry = build_registry()


def get_registry() -> ProviderRegistry:
    return registry
