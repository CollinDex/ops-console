import pytest

from app.core.config import Settings, normalise_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql+psycopg://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
    ],
)
def test_database_url_is_normalised(raw: str, expected: str) -> None:
    assert normalise_database_url(raw) == expected
    assert Settings(database_url=raw).database_url == expected


def test_cors_origins_accepts_comma_separated_list() -> None:
    s = Settings(cors_origins="https://a.vercel.app, https://b.vercel.app/")  # type: ignore[arg-type]
    assert s.cors_origins == ["https://a.vercel.app", "https://b.vercel.app"]


def test_cors_origins_accepts_json_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')
    assert Settings().cors_origins == ["http://localhost:3000"]
