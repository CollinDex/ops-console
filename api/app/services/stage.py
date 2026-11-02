"""Onboarding stage derivation (design section 5.3). Pure: no DB access."""

from collections.abc import Mapping
from datetime import datetime

from app.models.enums import CheckStatus, CheckType, Stage

_PRE_CHECK_STAGES = frozenset({Stage.signed_up, Stage.documents_submitted})


def derive_stage(
    current: Stage,
    checks: Mapping[CheckType, CheckStatus],
    consent_given_at: datetime | None,
) -> Stage:
    """Return the stage a business should be in after a check update.

    The console never moves a business out of (or back into) the two pre-check stages.
    """
    if current in _PRE_CHECK_STAGES:
        return current
    if all(checks.get(t) == CheckStatus.passed for t in CheckType):
        return Stage.profile_ready if consent_given_at is not None else Stage.bank_linked
    return Stage.checks_in_progress
