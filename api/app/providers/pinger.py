"""Background provider ping loop (design section 7.4)."""

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.models import IdempotencyKey, ProviderPing
from app.models.enums import PingStatus, ProviderName
from app.providers.base import CALL_TIMEOUT_S, PingResult
from app.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

PING_RETENTION = timedelta(days=7)
KEY_RETENTION = timedelta(hours=24)
CLEANUP_EVERY_S = 3600.0

SessionFactory = Callable[[], Session]


async def _safe_ping(registry: ProviderRegistry, name: ProviderName) -> PingResult:
    try:
        return await asyncio.wait_for(registry.get(name).ping(), CALL_TIMEOUT_S)
    except Exception as exc:
        error = (str(exc) or type(exc).__name__)[:200]
        return PingResult(PingStatus.down, None, error)


def _insert(
    session_factory: SessionFactory, rows: Sequence[tuple[ProviderName, PingResult]]
) -> None:
    now = datetime.now(UTC)
    with session_factory() as db:
        db.execute(
            insert(ProviderPing),
            [
                {
                    "provider": name,
                    "status": result.status,
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                    "checked_at": now,
                }
                for name, result in rows
            ],
        )
        db.commit()


def _cleanup(session_factory: SessionFactory) -> None:
    now = datetime.now(UTC)
    with session_factory() as db:
        db.execute(delete(ProviderPing).where(ProviderPing.checked_at < now - PING_RETENTION))
        db.execute(delete(IdempotencyKey).where(IdempotencyKey.created_at < now - KEY_RETENTION))
        db.commit()


async def ping_once(
    registry: ProviderRegistry,
    session_factory: SessionFactory,
    names: Sequence[ProviderName] | None = None,
) -> None:
    """Ping the given providers (default all) at once and record one row each."""
    chosen = list(names) if names is not None else [p.name for p in registry.all()]
    results = await asyncio.gather(*(_safe_ping(registry, n) for n in chosen))
    await asyncio.to_thread(_insert, session_factory, list(zip(chosen, results, strict=True)))


async def run_pinger(
    registry: ProviderRegistry,
    session_factory: SessionFactory,
    *,
    stop: asyncio.Event,
    interval: float = 15.0,
) -> None:
    """Loop until `stop` is set. An iteration that fails is logged and never ends the loop."""
    last_cleanup: float | None = None
    while not stop.is_set():
        try:
            await ping_once(registry, session_factory)
            if last_cleanup is None or time.monotonic() - last_cleanup >= CLEANUP_EVERY_S:
                await asyncio.to_thread(_cleanup, session_factory)
                last_cleanup = time.monotonic()
        except Exception:
            logger.exception("pinger iteration failed")
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), interval)
