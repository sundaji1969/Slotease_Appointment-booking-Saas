from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, Unauthorized
from app.core.security import burn_password_check, create_access_token, hash_password, verify_password
from app.models import Business
from app.repositories import businesses as business_repo
from app.repositories import users as user_repo
from app.schemas.auth import LoginIn, RegisterIn

LOGIN_FAILED = "Invalid email or password"


def register(db: Session, data: RegisterIn) -> tuple[str, Business]:
    """Create business + owner in ONE transaction."""
    if business_repo.slug_exists(db, data.slug):
        raise Conflict("SLUG_TAKEN", "That booking link is already taken")
    if user_repo.email_exists(db, data.email):
        raise Conflict("EMAIL_TAKEN", "An account with that email already exists")
    try:
        biz = business_repo.create_business(db, name=data.business_name, slug=data.slug, phone=data.phone)
        user = user_repo.create_user(db, biz.id, data.email, hash_password(data.password), role="owner")
        db.commit()
    except IntegrityError as exc:  # lost a race on slug/email
        db.rollback()
        detail = str(exc.orig)
        if "slug" in detail:
            raise Conflict("SLUG_TAKEN", "That booking link is already taken") from exc
        raise Conflict("EMAIL_TAKEN", "An account with that email already exists") from exc
    return create_access_token(user.id, biz.id, user.role), biz


def login(db: Session, data: LoginIn) -> str:
    user = user_repo.get_by_email(db, data.email)
    if user is None:
        burn_password_check(data.password)
        raise Unauthorized(LOGIN_FAILED, code="INVALID_CREDENTIALS")
    if not verify_password(data.password, user.password_hash):
        raise Unauthorized(LOGIN_FAILED, code="INVALID_CREDENTIALS")
    return create_access_token(user.id, user.business_id, user.role)
