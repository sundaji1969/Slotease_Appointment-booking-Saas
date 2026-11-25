"""Phase 2: the database itself must make double booking impossible."""

import uuid
from collections.abc import Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal

IST = ZoneInfo("Asia/Kolkata")


def at(h: int, m: int = 0) -> datetime:
    return datetime(2026, 10, 10, h, m, tzinfo=IST)


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as s:
        yield s


def _business(db: Session, slug: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    bid, sid, cid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    db.execute(
        text("INSERT INTO businesses (id, name, slug) VALUES (:id, :n, :s)"),
        {"id": bid, "n": slug, "s": slug},
    )
    db.execute(
        text(
            "INSERT INTO services (id, business_id, name, duration_min, price) VALUES (:id, :b, 'Cut', 30, 300)"
        ),
        {"id": sid, "b": bid},
    )
    db.execute(
        text("INSERT INTO customers (id, business_id, name, phone) VALUES (:id, :b, 'C', '+919999999999')"),
        {"id": cid, "b": bid},
    )
    db.commit()
    return bid, sid, cid


def _appt(
    db: Session,
    ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    start: datetime,
    end: datetime,
    status: str = "booked",
) -> None:
    bid, sid, cid = ids
    db.execute(
        text(
            "INSERT INTO appointments (id, public_ref, business_id, service_id, customer_id, start_time, end_time, status)"
            " VALUES (:id, :ref, :b, :s, :c, :st, :en, :status)"
        ),
        {
            "id": uuid.uuid4(),
            "ref": uuid.uuid4().hex,
            "b": bid,
            "s": sid,
            "c": cid,
            "st": start,
            "en": end,
            "status": status,
        },
    )
    db.commit()


def test_same_start_time_twice_rejected(db: Session) -> None:
    ids = _business(db, "biz-one")
    _appt(db, ids, at(17, 30), at(18))
    with pytest.raises(IntegrityError):
        _appt(db, ids, at(17, 30), at(18))


def test_overlapping_different_start_rejected(db: Session) -> None:
    ids = _business(db, "biz-one")
    _appt(db, ids, at(17, 30), at(18, 15))
    with pytest.raises(IntegrityError) as e:
        _appt(db, ids, at(17, 45), at(18, 15))
    assert "no_overlapping_appointments" in str(e.value)


def test_back_to_back_allowed(db: Session) -> None:
    ids = _business(db, "biz-one")
    _appt(db, ids, at(17), at(17, 30))
    _appt(db, ids, at(17, 30), at(18))


def test_cancelled_slot_can_be_rebooked(db: Session) -> None:
    ids = _business(db, "biz-one")
    _appt(db, ids, at(17, 30), at(18), status="cancelled")
    _appt(db, ids, at(17, 30), at(18))


def test_no_show_does_not_block(db: Session) -> None:
    ids = _business(db, "biz-one")
    _appt(db, ids, at(17, 30), at(18), status="no_show")
    _appt(db, ids, at(17, 30), at(18))


def test_completed_still_blocks(db: Session) -> None:
    ids = _business(db, "biz-one")
    _appt(db, ids, at(17, 30), at(18), status="completed")
    with pytest.raises(IntegrityError):
        _appt(db, ids, at(17, 45), at(18, 15))


def test_same_slot_in_two_businesses_allowed(db: Session) -> None:
    a = _business(db, "biz-one")
    b = _business(db, "biz-two")
    _appt(db, a, at(17, 30), at(18))
    _appt(db, b, at(17, 30), at(18))


def test_end_before_start_rejected(db: Session) -> None:
    ids = _business(db, "biz-one")
    with pytest.raises(IntegrityError):
        _appt(db, ids, at(18), at(17))
