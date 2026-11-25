from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time(0), tzinfo=tz)
    return start, datetime.combine(day + timedelta(days=1), time(0), tzinfo=tz)


def month_bounds(year: int, month: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=tz)
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=tz)
    return start, end
