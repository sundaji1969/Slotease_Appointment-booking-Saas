"""SQLAlchemy models. The authoritative constraints live in the Alembic migration (alembic/versions)."""

import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _business_fk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="Asia/Kolkata")
    slot_step_min: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="trial")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('owner','staff')", name="ck_users_role"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = _business_fk()
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("duration_min BETWEEN 5 AND 480", name="ck_services_duration"),
        CheckConstraint("price >= 0", name="ck_services_price"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = _business_fk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WorkingHour(Base):
    __tablename__ = "working_hours"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_hours_weekday"),
        CheckConstraint("close_time > open_time", name="ck_hours_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = _business_fk()
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0 = Monday
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("business_id", "phone", name="uq_customers_business_phone"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = _business_fk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_appt_order"),
        CheckConstraint("status IN ('booked','completed','cancelled','no_show')", name="ck_appt_status"),
        UniqueConstraint("business_id", "public_ref", name="uq_appt_business_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_ref: Mapped[str] = mapped_column(Text, nullable=False)
    business_id: Mapped[uuid.UUID] = _business_fk()
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="booked")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
