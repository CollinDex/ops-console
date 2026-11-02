import itertools
from datetime import UTC, datetime

import pytest

from app.models.enums import CheckStatus, CheckType, Stage
from app.services.stage import derive_stage

CONSENT = datetime(2026, 11, 1, tzinfo=UTC)
COMBOS = list(itertools.product(CheckStatus, repeat=len(CheckType)))


@pytest.mark.parametrize("current", list(Stage))
@pytest.mark.parametrize("consent", [None, CONSENT], ids=["no_consent", "consent"])
def test_derive_stage_matrix(current: Stage, consent: datetime | None) -> None:
    assert len(COMBOS) == 81
    for combo in COMBOS:
        checks = dict(zip(CheckType, combo, strict=True))
        result = derive_stage(current, checks, consent)
        if current in (Stage.signed_up, Stage.documents_submitted):
            expected = current
        elif all(s == CheckStatus.passed for s in combo):
            expected = Stage.profile_ready if consent else Stage.bank_linked
        else:
            expected = Stage.checks_in_progress
        assert result == expected, (current, combo, consent)


def test_missing_checks_count_as_not_passed() -> None:
    partial = {CheckType.cac: CheckStatus.passed}
    assert derive_stage(Stage.bank_linked, partial, CONSENT) == Stage.checks_in_progress
