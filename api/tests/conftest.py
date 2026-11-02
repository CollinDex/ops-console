import os

from app.core.config import Settings

# Point the app at the test database before anything imports the engine.
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = Settings().test_database_url
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"
os.environ["BCRYPT_ROUNDS"] = "4"  # fast hashing in tests; production default is 12

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.db.session import engine, get_db  # noqa: E402
from app.main import create_app  # noqa: E402


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


@pytest.fixture
def app(db: Session) -> FastAPI:
    application = create_app()

    def _get_db() -> Iterator[Session]:
        yield db

    application.dependency_overrides[get_db] = _get_db
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
