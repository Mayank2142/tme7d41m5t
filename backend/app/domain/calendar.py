"""UK civil-day boundaries and the deliberately bounded assignment calendar."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from backend.app.domain.policy import PILOT_POLICY

LONDON = ZoneInfo("Europe/London")


def parse_cutoff(value: str) -> time:
    if not re.fullmatch(r"[0-9]{2}:[0-9]{2}", value):
        raise ValueError("Cutoff must use local HH:MM format")
    return time.fromisoformat(value)


def uk_day_bounds(day: date) -> tuple[datetime, datetime]:
    """Construct both midnights locally; a UK day can have 23, 24, or 25 hours."""
    return (
        datetime.combine(day, time.min, LONDON).astimezone(UTC),
        datetime.combine(day + timedelta(days=1), time.min, LONDON).astimezone(UTC),
    )


def target_grid(start: datetime, end: datetime, minutes: int) -> tuple[datetime, ...]:
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("Target boundaries must be timezone-aware")
    start, end = start.astimezone(UTC), end.astimezone(UTC)
    if minutes not in {30, 60} or end <= start:
        raise ValueError("Invalid target grid")
    step = timedelta(minutes=minutes)
    if (end - start) % step:
        raise ValueError("Target boundaries must cover whole intervals")
    return tuple(start + index * step for index in range((end - start) // step))


def decision_dates(start: date, end: date) -> tuple[date, ...]:
    if isinstance(start, datetime) or isinstance(end, datetime):
        raise ValueError("Decision dates must be calendar dates")
    if not PILOT_POLICY.decision_from <= start <= end <= PILOT_POLICY.decision_to:
        raise ValueError("Decision dates must be an inclusive range within January 2026")
    return tuple(start + timedelta(days=index) for index in range((end - start).days + 1))


@dataclass(frozen=True)
class DecisionWindow:
    decision_date: date
    delivery_date: date
    cutoff_local: str
    cutoff_utc: datetime
    delivery_start_utc: datetime
    delivery_end_utc: datetime
    timezone: str = PILOT_POLICY.timezone


def decision_window(day: date, cutoff: time) -> DecisionWindow:
    decision_dates(day, day)
    if cutoff.tzinfo is not None or cutoff.second or cutoff.microsecond or cutoff.fold:
        raise ValueError("Cutoff must be a local HH:MM value without an offset")
    delivery_date = day + timedelta(days=1)
    start, end = uk_day_bounds(delivery_date)
    return DecisionWindow(
        day,
        delivery_date,
        cutoff.isoformat(timespec="minutes"),
        datetime.combine(day, cutoff, LONDON).astimezone(UTC),
        start,
        end,
    )
