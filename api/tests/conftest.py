import os

from app.core.config import Settings

# Point the app at the test database before anything imports the engine.
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = Settings().test_database_url
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"
os.environ["BCRYPT_ROUNDS"] = "4"  # fast hashing in tests; production default is 12

import asyncio  # noqa: E402
import random  # noqa: E402
from collections.abc import Iterator  # noqa: E402
from types import TracebackType  # noqa: E402

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.db.session import engine, get_db, get_session_factory  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.enums import ProviderName  # noqa: E402
from app.providers.registry import (  # noqa: E402
    ProviderRegistry,
    get_registry,
)
from app.providers.simulator import SimulatedProvider  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    """Rebuild the test schema from the migrations once per run."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def db() -> Iterator[Session]:
    """A session inside an outer transaction that is rolled back after the test."""
    conn = engine.connect()
    outer = conn.begin()
    session = Session(
        bind=conn,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        conn.close()


async def fast_sleep(_seconds: float) -> None:
    await asyncio.sleep(0)


def make_registry(sleep=fast_sleep, pass_rate: float = 0.8) -> ProviderRegistry:  # type: ignore[no-untyped-def]
    """A seeded registry whose providers do not really wait."""
    return ProviderRegistry(
        [
            SimulatedProvider(n, random.Random(1), sleep=sleep, pass_rate=pass_rate)
            for n in ProviderName
        ]
    )


@pytest.fixture
def registry() -> ProviderRegistry:
    return make_registry()


class SharedSession:
    """Session factory that hands back the test session and never closes it."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def __call__(self) -> "SharedSession":
        return self

    def __enter__(self) -> Session:
        return self.session

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


@pytest.fixture
def app(db: Session, registry: ProviderRegistry) -> FastAPI:
    application = create_app()

    def _get_db() -> Iterator[Session]:
        yield db

    application.dependency_overrides[get_db] = _get_db
    application.dependency_overrides[get_registry] = lambda: registry
    application.dependency_overrides[get_session_factory] = lambda: SharedSession(db)
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def analyst_headers(client: TestClient, db: Session) -> dict[str, str]:
    from app.models.enums import Role
    from tests.factories import auth_header, make_staff

    user = make_staff(db, role=Role.analyst, password="Passw0rd!test")
    return auth_header(client, user.email, "Passw0rd!test")


@pytest.fixture
def viewer_headers(client: TestClient, db: Session) -> dict[str, str]:
    from app.models.enums import Role
    from tests.factories import auth_header, make_staff

    user = make_staff(db, role=Role.viewer, password="Passw0rd!test")
    return auth_header(client, user.email, "Passw0rd!test")


@pytest.fixture
def admin_headers(client: TestClient, db: Session) -> dict[str, str]:
    from app.models.enums import Role
    from tests.factories import auth_header, make_staff

    user = make_staff(db, role=Role.ops_admin, password="Passw0rd!test")
    return auth_header(client, user.email, "Passw0rd!test")
