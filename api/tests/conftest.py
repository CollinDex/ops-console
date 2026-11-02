import os

from app.core.config import Settings

# Point the app at the test database before anything imports the engine.
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = Settings().test_database_url

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c
