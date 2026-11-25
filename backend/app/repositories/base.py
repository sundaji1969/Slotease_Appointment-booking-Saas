import uuid
from typing import Any, cast

from sqlalchemy import Select


def scoped[S: Select[*tuple[Any, ...]]](stmt: S, model: Any, business_id: uuid.UUID) -> S:
    """Restrict any SELECT to one tenant. Every owner-facing query must pass through this."""
    return cast(S, stmt.where(model.business_id == business_id))
