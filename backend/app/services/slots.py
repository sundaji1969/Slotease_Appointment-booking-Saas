"""Pure slot calculation (GUIDE A6). No database access and no clock reads: `now` is injected.

The slot list is a hint for the UI. The real guarantee against double booking is the
`no_overlapping_appointments` EXCLUDE constraint at insert time.
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

Window = tuple[time, time]
Interval = tuple[datetime, datetime]


class SlotError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Half-open interval overlap: [a_start, a_end) ∩ [b_start, b_end) ≠ ∅."""
    return a_start < b_end and b_start < a_end


def validate_day(day: date, tz: ZoneInfo, now: datetime, max_days_ahead: int = 60) -> None:
    today = now.astimezone(tz).date()
    if day < today:
        raise SlotError("PAST_DATE", "That date is in the past.")
    if day > today + timedelta(days=max_days_ahead):
        raise SlotError("TOO_FAR_AHEAD", f"Bookings open at most {max_days_ahead} days ahead.")


def compute_free_slots(
    day: date,
    tz: ZoneInfo,
    working_windows: Sequence[Window],
    busy: Sequence[Interval],
    duration_min: int,
    step_min: int,
    now: datetime,
    lead_time_min: int = 30,
    max_days_ahead: int = 60,
) -> list[datetime]:
    """Return free start times (aware datetimes in `tz`) for a service of `duration_min` on `day`."""
    if duration_min <= 0 or step_min <= 0:
        raise ValueError("duration_min and step_min must be positive")
    validate_day(day, tz, now, max_days_ahead)

    duration = timedelta(minutes=duration_min)
    step = timedelta(minutes=step_min)
    earliest = now + timedelta(minutes=lead_time_min)

    free: set[datetime] = set()
    for open_t, close_t in working_windows:
        t = datetime.combine(day, open_t, tzinfo=tz)
        close = datetime.combine(day, close_t, tzinfo=tz)
        while t + duration <= close:
            end = t + duration
            if t >= earliest and not any(overlaps(t, end, b_start, b_end) for b_start, b_end in busy):
                free.add(t)
            t += step
    return sorted(free)


def check_bookable_start(
    start: datetime,
    tz: ZoneInfo,
    working_windows: Sequence[Window],
    duration_min: int,
    step_min: int,
    now: datetime,
    lead_time_min: int = 30,
    max_days_ahead: int = 60,
) -> None:
    """Re-validate a client-supplied start time: inside working hours, on the slot grid, not too soon.

    Raises SlotError with code OUTSIDE_HOURS / OFF_GRID / TOO_SOON / PAST_DATE / TOO_FAR_AHEAD.
    Existing bookings are NOT checked here — that is the database's job.
    """
    local = start.astimezone(tz)
    validate_day(local.date(), tz, now, max_days_ahead)
    duration = timedelta(minutes=duration_min)

    for open_t, close_t in working_windows:
        w_open = datetime.combine(local.date(), open_t, tzinfo=tz)
        w_close = datetime.combine(local.date(), close_t, tzinfo=tz)
        if w_open <= local and local + duration <= w_close:
            offset = local - w_open
            if offset % timedelta(minutes=step_min) != timedelta(0):
                raise SlotError("OFF_GRID", f"Start time must be on a {step_min}-minute slot.")
            if local < now + timedelta(minutes=lead_time_min):
                raise SlotError("TOO_SOON", f"Bookings need at least {lead_time_min} minutes notice.")
            return
    raise SlotError("OUTSIDE_HOURS", "That time is outside the business's working hours.")
