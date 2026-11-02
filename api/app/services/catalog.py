"""Labels and score bands, defined once and reused by meta, stats and CSV."""

from typing import TypedDict

from app.models.enums import CheckType, ProviderName, Sector, Stage


class ScoreBand(TypedDict):
    key: str
    label: str
    min: int
    max: int


STAGE_LABELS: dict[Stage, str] = {
    Stage.signed_up: "Signed up",
    Stage.documents_submitted: "Documents submitted",
    Stage.checks_in_progress: "Checks in progress",
    Stage.bank_linked: "Bank linked",
    Stage.profile_ready: "Profile ready",
}

SECTOR_LABELS: dict[Sector, str] = {s: s.value.replace("_", " ").capitalize() for s in Sector}

CHECK_LABELS: dict[CheckType, str] = {
    CheckType.cac: "CAC",
    CheckType.tin: "Tax ID",
    CheckType.bvn: "BVN",
    CheckType.bank_link: "Bank link",
}

SCORE_BANDS: list[ScoreBand] = [
    {"key": "poor", "label": "Poor", "min": 300, "max": 579},
    {"key": "fair", "label": "Fair", "min": 580, "max": 669},
    {"key": "good", "label": "Good", "min": 670, "max": 739},
    {"key": "very_good", "label": "Very good", "min": 740, "max": 799},
    {"key": "excellent", "label": "Excellent", "min": 800, "max": 850},
]

PROVIDER_LABELS: dict[ProviderName, str] = {
    ProviderName.bvn: "BVN (NIBSS)",
    ProviderName.cac: "CAC registry",
    ProviderName.tin: "Tax ID (FIRS)",
    ProviderName.open_banking: "Open banking",
}

# Shared by the seed and the simulated providers so both produce the same failure messages.
FAILURE_REASONS: dict[CheckType, list[str]] = {
    CheckType.cac: [
        "CAC number not found in registry",
        "Company name does not match CAC record",
        "Company status is inactive",
    ],
    CheckType.tin: [
        "TIN not registered with FIRS",
        "TIN does not match company name",
    ],
    CheckType.bvn: [
        "BVN name does not match director",
        "BVN date of birth mismatch",
        "BVN record not found",
    ],
    CheckType.bank_link: [
        "Account name does not match company name",
        "Bank consent expired",
        "Statement fetch timed out",
    ],
}
