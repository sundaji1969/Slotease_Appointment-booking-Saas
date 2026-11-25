from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.ratelimit import AUTH_LIMIT, limiter
from app.deps.db import get_db
from app.schemas.auth import BusinessOut, LoginIn, RegisterIn, RegisterOut, TokenOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterOut)
@limiter.limit(AUTH_LIMIT)
def register(request: Request, data: RegisterIn, db: Session = Depends(get_db)) -> RegisterOut:
    token, biz = auth_service.register(db, data)
    return RegisterOut(access_token=token, business=BusinessOut.model_validate(biz))


@router.post("/login", response_model=TokenOut)
@limiter.limit(AUTH_LIMIT)
def login(request: Request, data: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    return TokenOut(access_token=auth_service.login(db, data))
