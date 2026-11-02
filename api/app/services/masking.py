"""Masking helpers (ADR-006). Only the last four digits are ever stored."""


def mask_bvn(last4: str) -> str:
    """A BVN has 11 digits: show the last four."""
    return "*" * 7 + last4


def mask_account(last4: str) -> str:
    """A NUBAN account number has 10 digits: show the last four."""
    return "*" * 6 + last4
