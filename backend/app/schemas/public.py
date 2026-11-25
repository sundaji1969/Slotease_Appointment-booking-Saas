import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.phone import normalize_indian_phone


class PublicBusinessOut(BaseModel):
    name: str
    slug: str
    phone: str | None
    timezone: str
    assistant_enabled: bool = False


class PublicServiceOut(BaseModel):
    id: uuid.UUID
    name: str
    duration_min: int
    price: float


class SlotsOut(BaseModel):
    date: date
    slots: list[datetime]


class BookingIn(BaseModel):
    service_id: uuid.UUID
    start_time: datetime
    name: str = Field(min_length=2, max_length=60)
    phone: str

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_indian_phone(v)


class BookingOut(BaseModel):
    booking_id: str
    service: str
    start_time: datetime
    end_time: datetime
    status: str
    message: str


class AssistantTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=500)


class AssistantIn(BaseModel):
    message: str = Field(min_length=1, max_length=300)
    history: list[AssistantTurn] = Field(default_factory=list, max_length=10)


class AssistantOut(BaseModel):
    reply: str
    service_id: uuid.UUID | None
    date: date | None
    slots: list[datetime]
