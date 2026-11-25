"""A12 'Unit — slots.py': the pure slot function, exhaustively."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services.slots import SlotError, check_bookable_start, compute_free_slots, overlaps

IST = ZoneInfo("Asia/Kolkata")
DAY = date(2026, 10, 10)  # Saturday
EARLY_NOW = datetime(2026, 10, 9, 9, 0, tzinfo=IST)  # the day before, so lead time never matters
SPLIT = [(time(10), time(13)), (time(14), time(20))]


def at(h: int, m: int = 0, day: date = DAY) -> datetime:
    return datetime.combine(day, time(h, m), tzinfo=IST)


def hm(slots: list[datetime]) -> list[str]:
    return [s.strftime("%H:%M") for s in slots]


def free(**kw):  # type: ignore[no-untyped-def]
    args = dict(day=DAY, tz=IST, working_windows=SPLIT, busy=[], duration_min=30, step_min=15, now=EARLY_NOW)
    args.update(kw)
    return compute_free_slots(**args)  # type: ignore[arg-type]


def test_open_and_close_edges() -> None:
    s = hm(free(working_windows=[(time(10), time(11))]))
    assert s[0] == "10:00"  # first slot exactly at opening
    assert s[-1] == "10:30"  # 10:30-11:00 ends exactly at close
    assert "10:45" not in s  # 10:45-11:15 would overrun close


def test_lunch_break_is_respected() -> None:
    s = hm(free())
    assert "12:30" in s  # 12:30-13:00 fits before lunch
    assert "12:45" not in s  # 12:45-13:15 runs into lunch
    assert "13:00" not in s and "13:30" not in s
    assert "14:00" in s


def test_duration_not_fitting_before_close() -> None:
    s = hm(free(duration_min=45, working_windows=[(time(19), time(20))]))
    assert s == ["19:00", "19:15"]


def test_back_to_back_booking_is_allowed() -> None:
    busy = [(at(17), at(17, 30))]
    s = hm(free(busy=busy))
    assert "17:30" in s  # starts exactly when the busy one ends
    assert "16:30" in s  # ends exactly when the busy one starts
    assert "17:00" not in s and "17:15" not in s and "16:45" not in s


def test_overlapping_busy_interval_blocks_all_overlapping_candidates() -> None:
    busy = [(at(17, 30), at(18, 15))]  # 45-minute Haircut + Beard
    s = hm(free(busy=busy, duration_min=30))
    for blocked in ("17:15", "17:30", "17:45", "18:00"):
        assert blocked not in s
    assert "17:00" in s and "18:15" in s


def test_lead_time_hides_slots_too_soon() -> None:
    now = at(11, 0)
    s = hm(free(now=now, lead_time_min=30))
    assert "11:15" not in s
    assert s[0] == "11:30"


def test_past_date_rejected() -> None:
    with pytest.raises(SlotError) as e:
        free(day=DAY - timedelta(days=2))
    assert e.value.code == "PAST_DATE"


def test_more_than_60_days_ahead_rejected() -> None:
    with pytest.raises(SlotError) as e:
        free(day=EARLY_NOW.date() + timedelta(days=61))
    assert e.value.code == "TOO_FAR_AHEAD"
    assert free(day=EARLY_NOW.date() + timedelta(days=60))  # boundary is allowed


def test_today_is_allowed_with_lead_time() -> None:
    now = at(19, 0)
    s = hm(free(now=now))
    assert s == ["19:30"]


def test_ist_has_no_dst_and_returns_offset_aware_ist() -> None:
    s = free()
    assert all(x.utcoffset() == timedelta(hours=5, minutes=30) for x in s)
    assert s[0].isoformat() == "2026-10-10T10:00:00+05:30"


def test_step_15_vs_30() -> None:
    w = [(time(10), time(11))]
    assert hm(free(working_windows=w, step_min=15)) == ["10:00", "10:15", "10:30"]
    assert hm(free(working_windows=w, step_min=30)) == ["10:00", "10:30"]


def test_closed_day_has_no_slots() -> None:
    assert free(working_windows=[]) == []


def test_busy_given_in_utc_is_compared_correctly() -> None:
    utc = ZoneInfo("UTC")
    busy = [(at(17).astimezone(utc), at(17, 30).astimezone(utc))]
    assert "17:00" not in hm(free(busy=busy))


def test_results_sorted_and_unique_with_overlapping_windows() -> None:
    s = free(working_windows=[(time(10), time(11)), (time(10), time(11))])
    assert s == sorted(set(s))


def test_overlaps_is_half_open() -> None:
    assert not overlaps(at(17), at(17, 30), at(17, 30), at(18))
    assert overlaps(at(17), at(17, 31), at(17, 30), at(18))


@pytest.mark.parametrize(
    ("start", "code"),
    [
        (at(9, 45), "OUTSIDE_HOURS"),
        (at(12, 45), "OUTSIDE_HOURS"),  # runs into lunch
        (at(19, 45), "OUTSIDE_HOURS"),  # runs past close
        (at(17, 10), "OFF_GRID"),
    ],
)
def test_check_bookable_start_rejects(start: datetime, code: str) -> None:
    with pytest.raises(SlotError) as e:
        check_bookable_start(start, IST, SPLIT, 30, 15, EARLY_NOW)
    assert e.value.code == code


def test_check_bookable_start_too_soon() -> None:
    with pytest.raises(SlotError) as e:
        check_bookable_start(at(11, 15), IST, SPLIT, 30, 15, at(11, 0))
    assert e.value.code == "TOO_SOON"


def test_check_bookable_start_accepts_grid_slot() -> None:
    check_bookable_start(at(17, 30), IST, SPLIT, 45, 15, EARLY_NOW)
