"""Enums shared by the ORM models. Stored as native Postgres enums."""

from enum import StrEnum


class Role(StrEnum):
    ops_admin = "ops_admin"
    analyst = "analyst"
    viewer = "viewer"


class Stage(StrEnum):
    # Declaration order is the funnel order.
    signed_up = "signed_up"
    documents_submitted = "documents_submitted"
    checks_in_progress = "checks_in_progress"
    bank_linked = "bank_linked"
    profile_ready = "profile_ready"


class CheckType(StrEnum):
    cac = "cac"
    tin = "tin"
    bvn = "bvn"
    bank_link = "bank_link"


class CheckStatus(StrEnum):
    pending = "pending"
    passed = "passed"
    failed = "failed"


class Sector(StrEnum):
    agriculture = "agriculture"
    retail = "retail"
    manufacturing = "manufacturing"
    logistics = "logistics"
    technology = "technology"
    healthcare = "healthcare"
    hospitality = "hospitality"
    construction = "construction"
    fashion = "fashion"
    education = "education"


class ProviderName(StrEnum):
    bvn = "bvn"
    cac = "cac"
    tin = "tin"
    open_banking = "open_banking"


class PingStatus(StrEnum):
    up = "up"
    slow = "slow"
    down = "down"
