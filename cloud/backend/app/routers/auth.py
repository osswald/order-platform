from datetime import timedelta
import os

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth_sessions import invalidate_user_sessions, session_claims, token_version_matches
from ..deps import get_db
from ..rate_limit import LOGIN_RATE_LIMIT, REFRESH_RATE_LIMIT, limiter
from ..models import HireCompany, User
from ..user_access import is_org_admin, is_platform_admin, user_hire_company_id, user_role
from ..schemas import MessageResponse
from ..auth_deps import get_current_user
from ..i18n.errors import api_error
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)

router = APIRouter()


class HireCompanyBrief(BaseModel):
    id: int
    name: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False
    user_id: int | None = None
    role: str = "member"
    hire_company_id: int | None = None
    is_tenant_admin: bool = False


class MeResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
    name: str | None = None
    role: str = "member"
    hire_company_id: int | None = None
    is_tenant_admin: bool = False
    hire_companies: list[HireCompanyBrief] = []


def _token_for_user(user: User) -> dict:
    role = user_role(user)
    return {
        "is_admin": is_platform_admin(user),
        "role": role,
        "hire_company_id": user_hire_company_id(user),
        "is_tenant_admin": is_org_admin(user),
    }


def _refresh_cookie_params() -> dict:
    return {
        "max_age": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")) * 24 * 3600,
        "secure": os.getenv("REFRESH_COOKIE_SECURE", "false").lower() == "true",
        "httponly": True,
        "samesite": "lax",
        "path": "/",
    }


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(key="refresh_token", value=refresh_token, **_refresh_cookie_params())


def _clear_refresh_cookie(response: Response) -> None:
    params = _refresh_cookie_params()
    response.delete_cookie(
        key="refresh_token",
        path=params["path"],
        secure=params["secure"],
        samesite=params["samesite"],
    )


def _issue_session_tokens(user: User, response: Response) -> tuple[str, str]:
    claims = session_claims(user)
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    access_token = create_access_token(data=claims, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data=claims)
    _set_refresh_cookie(response, refresh_token)
    return access_token, refresh_token


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=1)


@router.post("/token", response_model=Token)
@limiter.limit(LOGIN_RATE_LIMIT)
def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        exc = api_error("incorrect_email_or_password", status.HTTP_401_UNAUTHORIZED)
        exc.headers = {"WWW-Authenticate": "Bearer"}
        raise exc
    access_token, _refresh = _issue_session_tokens(user, response)
    flags = _token_for_user(user)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        **flags,
    )


@router.get("/me", response_model=MeResponse)
def read_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    flags = _token_for_user(current_user)
    hire_companies: list[HireCompanyBrief] = []
    if is_platform_admin(current_user):
        rows = db.query(HireCompany).order_by(HireCompany.name).all()
        hire_companies = [HireCompanyBrief(id=c.id, name=c.name) for c in rows]
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        hire_companies=hire_companies,
        **flags,
    )


@router.post("/refresh", response_model=Token)
@limiter.limit(REFRESH_RATE_LIMIT)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Token:
    token = request.cookies.get("refresh_token")
    if not token:
        raise api_error("missing_refresh_token", status.HTTP_401_UNAUTHORIZED)
    try:
        payload = decode_refresh_token(token)
    except Exception:
        raise api_error("invalid_refresh_token", status.HTTP_401_UNAUTHORIZED)
    email = payload.get("sub")
    if not email:
        raise api_error("invalid_refresh_token", status.HTTP_401_UNAUTHORIZED)
    user = db.query(User).filter(User.email == email).first()
    if not user or not token_version_matches(user, payload):
        raise api_error("invalid_refresh_token", status.HTTP_401_UNAUTHORIZED)
    invalidate_user_sessions(user, db)
    access_token, _refresh = _issue_session_tokens(user, response)
    flags = _token_for_user(user)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        **flags,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> MessageResponse:
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = decode_refresh_token(token)
            email = payload.get("sub")
            if email:
                user = db.query(User).filter(User.email == email).first()
                if user:
                    invalidate_user_sessions(user, db)
        except Exception:
            pass
    _clear_refresh_cookie(response)
    return MessageResponse(msg="logged out")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    password_in: PasswordChange,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user or not verify_password(password_in.current_password, user.hashed_password):
        raise api_error("current_password_incorrect", status.HTTP_400_BAD_REQUEST)
    user.hashed_password = get_password_hash(password_in.new_password)
    invalidate_user_sessions(user, db)
    _clear_refresh_cookie(response)
    return MessageResponse(msg="password changed")
