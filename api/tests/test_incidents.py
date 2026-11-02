from datetime import UTC, datetime, timedelta

from app.models.enums import PingStatus
from app.services.providers import PingPoint, group_incidents

T0 = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)
NOW = T0 + timedelta(hours=1)


def _pings(*statuses: str) -> list[PingPoint]:
    return [PingPoint(T0 + timedelta(minutes=i), PingStatus(s)) for i, s in enumerate(statuses)]


def test_no_incidents() -> None:
    assert group_incidents(_pings("up", "up", "up"), NOW) == []
    assert group_incidents([], NOW) == []


def test_single_incident() -> None:
    [inc] = group_incidents(_pings("up", "down", "up"), NOW)
    assert inc.started_at == T0 + timedelta(minutes=1)
    assert inc.ended_at == T0 + timedelta(minutes=2)
    assert (inc.duration_seconds, inc.ping_count, inc.worst_status) == (60, 1, "down")


def test_consecutive_pings_form_one_incident() -> None:
    [inc] = group_incidents(_pings("up", "slow", "slow", "slow", "up"), NOW)
    assert inc.ping_count == 3
    assert inc.duration_seconds == 180
    assert inc.worst_status == "slow"


def test_two_separate_incidents() -> None:
    incidents = group_incidents(_pings("down", "up", "slow", "up"), NOW)
    assert [i.worst_status for i in incidents] == ["down", "slow"]


def test_ongoing_incident_has_no_end() -> None:
    [inc] = group_incidents(_pings("up", "down", "down"), NOW)
    assert inc.ended_at is None
    assert inc.duration_seconds == int((NOW - (T0 + timedelta(minutes=1))).total_seconds())


def test_slow_then_down_is_worst_down() -> None:
    [inc] = group_incidents(_pings("slow", "slow", "down", "up"), NOW)
    assert inc.worst_status == "down"
    assert inc.ping_count == 3
