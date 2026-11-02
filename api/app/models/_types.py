"""Helpers for building column types."""

from enum import StrEnum

import sqlalchemy as sa


def pg_enum[E: StrEnum](enum_cls: type[E], name: str) -> sa.Enum:
    """Native Postgres enum that stores the member values, not the names."""
    return sa.Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
