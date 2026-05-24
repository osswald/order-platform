from datetime import timedelta
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..deps import get_db
from ..rate_limit import LOGIN_RATE_LIMIT, limiter
from ..models import User
from ..schemas import MessageResponse
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires administrative privileges",
        )
    return current_user


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False
    user_id: int | None = None


class MeResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
    name: str | None = None


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    refresh_token = create_refresh_token(data={"sub": user.email})
    max_age = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")) * 24 * 3600
    secure_cookie = os.getenv("REFRESH_COOKIE_SECURE", "false").lower() == "true"
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
        max_age=max_age,
        path="/",
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        is_admin=user.is_superuser,
        user_id=user.id,
    )


@router.get("/me", response_model=MeResponse)
def read_me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        is_admin=current_user.is_superuser,
        name=current_user.name,
    )


@router.post("/refresh", response_model=Token)
def refresh_access_token(request: Request, db: Session = Depends(get_db)) -> Token:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    try:
        payload = decode_refresh_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    access_token = create_access_token(data={"sub": user.email})
    return Token(
        access_token=access_token,
        token_type="bearer",
        is_admin=user.is_superuser,
        user_id=user.id,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    response.delete_cookie("refresh_token", path="/")
    return MessageResponse(msg="logged out")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    password_in: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user or not verify_password(password_in.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.hashed_password = get_password_hash(password_in.new_password)
    db.commit()
    return MessageResponse(msg="password changed")
