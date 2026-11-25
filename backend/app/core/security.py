import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# A real hash used to equalise timing when the email doesn't exist (avoids user enumeration).
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode()


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    business_id: uuid.UUID
    role: str


def create_access_token(user_id: uuid.UUID, business_id: uuid.UUID, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "bid": str(business_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRE_MIN)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class InvalidToken(Exception):
    pass


def decode_access_token(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "bid", "role", "exp"]},
        )
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            business_id=uuid.UUID(payload["bid"]),
            role=str(payload["role"]),
        )
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise InvalidToken(str(exc)) from exc
