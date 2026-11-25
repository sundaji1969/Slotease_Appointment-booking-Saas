import re
import uuid
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from app.core.phone import normalize_indian_phone

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email(v: str) -> str:
    v = v.strip().lower()
    if len(v) > 254 or not EMAIL_RE.match(v):
        raise ValueError("Enter a valid email address")
    return v


Email = Annotated[str, AfterValidator(_email)]

SLUG_RE = re.compile(r"^[a-z0-9-]{3,40}$")
RESERVED_SLUGS = frozenset(
    {"login", "register", "dashboard", "api", "admin", "public", "auth", "docs", "health", "static", "assets"}
)


class RegisterIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=80)
    slug: str
    email: Email
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None

    @field_validator("business_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Business name is too short")
        return v

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not SLUG_RE.match(v):
            raise ValueError("Slug must be 3-40 characters: lowercase letters, digits and hyphens")
        if v in RESERVED_SLUGS:
            raise ValueError("That slug is reserved")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        return normalize_indian_phone(v)


class LoginIn(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=128)


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    phone: str | None
    timezone: str
    slot_step_min: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterOut(TokenOut):
    business: BusinessOut
