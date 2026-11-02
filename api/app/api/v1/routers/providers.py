"""Providers router: status, incident history and the demo simulate toggle."""

from typing import Annotated

import anyio.from_thread
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import NotFound
from app.core.security import get_current_user, require_roles
from app.db.session import get_db, get_session_factory
from app.models import StaffUser
from app.models.enums import ProviderName, Role
from app.providers.pinger import ping_once
from app.providers.registry import ProviderRegistry, get_registry
from app.schemas.providers import IncidentOut, ProvidersStatusOut, ProviderStatusOut, SimulateIn
from app.services import providers as svc
from app.services.audit import write_audit

router = APIRouter(prefix="/providers", tags=["providers"])

DbDep = Annotated[Session, Depends(get_db)]
RegistryDep = Annotated[ProviderRegistry, Depends(get_registry)]


def _provider_name(name: str) -> ProviderName:
    try:
        return ProviderName(name)
    except ValueError as exc:
        raise NotFound("Provider not found.") from exc


@router.get("/status", response_model=ProvidersStatusOut)
def providers_status(
    db: DbDep,
    registry: RegistryDep,
    _user: Annotated[StaffUser, Depends(get_current_user)],
) -> ProvidersStatusOut:
    return svc.provider_statuses(db, registry)


@router.get("/{name}/incidents", response_model=list[IncidentOut])
def provider_incidents(
    name: str,
    db: DbDep,
    _user: Annotated[StaffUser, Depends(get_current_user)],
) -> list[IncidentOut]:
    return svc.incidents_for(db, _provider_name(name))


@router.post("/{name}/simulate", response_model=ProviderStatusOut)
def simulate(
    name: str,
    body: SimulateIn,
    db: DbDep,
    registry: RegistryDep,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    user: Annotated[
        StaffUser, Depends(require_roles(Role.ops_admin, action="change provider simulation"))
    ],
) -> ProviderStatusOut:
    provider_name = _provider_name(name)
    provider = registry.get(provider_name)
    old = provider.mode
    provider.set_mode(body.mode)
    write_audit(
        db,
        actor_id=user.id,
        action="provider.simulate",
        target_type="provider",
        target_id=provider_name.value,
        details={"from": old, "to": body.mode},
    )
    db.commit()
    # This is a sync route (worker thread); hop to the event loop for the async ping.
    anyio.from_thread.run(ping_once, registry, session_factory, [provider_name])
    return svc.provider_statuses(db, registry, [provider_name]).providers[0]
