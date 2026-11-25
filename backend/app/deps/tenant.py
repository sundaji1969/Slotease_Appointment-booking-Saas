"""The ONLY source of business_id for owner endpoints: the verified JWT. Never the client."""

import uuid
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import Unauthorized
from app.core.security import InvalidToken, decode_access_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TenantContext:
    user_id: uuid.UUID
    business_id: uuid.UUID
    role: str


def get_current_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TenantContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthorized("Missing bearer token")
    try:
        claims = decode_access_token(credentials.credentials)
    except InvalidToken as exc:
        raise Unauthorized("Invalid or expired token", code="INVALID_TOKEN") from exc
    return TenantContext(user_id=claims.user_id, business_id=claims.business_id, role=claims.role)
