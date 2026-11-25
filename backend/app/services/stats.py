import re
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.errors import Unprocessable
from app.deps.tenant import TenantContext
from app.repositories import appointments as appt_repo
from app.schemas.owner import StatsOut
from app.services.owner import current_business
from app.services.timeutil import month_bounds

ISO_WEEKDAYS = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}
_MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def no_show_rate(completed: int, no_show: int) -> float:
    denom = completed + no_show
    return round(no_show / denom, 4) if denom else 0.0


def month_stats(db: Session, tenant: TenantContext, month: str) -> StatsOut:
    m = _MONTH_RE.match(month)
    if not m:
        raise Unprocessable("INVALID_MONTH", "month must look like YYYY-MM")
    biz = current_business(db, tenant)
    tz = ZoneInfo(biz.timezone)
    start, end = month_bounds(int(m.group(1)), int(m.group(2)), tz)
    s = appt_repo.month_stats(db, tenant.business_id, start, end, biz.timezone)
    return StatsOut(
        month=month,
        total=s.total,
        completed=s.completed,
        no_show=s.no_show,
        cancelled=s.cancelled,
        no_show_rate=no_show_rate(s.completed, s.no_show),
        revenue_estimate=float(s.revenue_estimate),
        busiest_weekday=ISO_WEEKDAYS.get(s.busiest_weekday) if s.busiest_weekday else None,
    )
