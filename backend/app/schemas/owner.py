import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AppointmentStatus = Literal["booked", "completed", "cancelled", "no_show"]


class AppointmentOut(BaseModel):
    id: uuid.UUID
    booking_id: str
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    customer_name: str
    customer_phone: str
    service_id: uuid.UUID
    service_name: str
    price: float
    whatsapp_url: str


class StatusPatch(BaseModel):
    status: AppointmentStatus


class ServiceIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    duration_min: int = Field(ge=5, le=480)
    price: Decimal = Field(ge=0, le=10_000_000, max_digits=10, decimal_places=2)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        return v


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    duration_min: int | None = Field(default=None, ge=5, le=480)
    price: Decimal | None = Field(default=None, ge=0, le=10_000_000, max_digits=10, decimal_places=2)
    is_active: bool | None = None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    duration_min: int
    price: float
    is_active: bool


class HourIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    open_time: time
    close_time: time

    @model_validator(mode="after")
    def _order(self) -> "HourIn":
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be after open_time")
        return self


class HourOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weekday: int
    open_time: time
    close_time: time


class TodayOut(BaseModel):
    date: date
    business_name: str
    count: int
    no_shows: int
    revenue_estimate: float


class StatsOut(BaseModel):
    month: str
    total: int
    completed: int
    no_show: int
    cancelled: int
    no_show_rate: float
    revenue_estimate: float
    busiest_weekday: str | None
