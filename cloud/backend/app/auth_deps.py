from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .auth_sessions import token_version_matches
from .deps import get_db
from .i18n.errors import api_error
from .models import User
from .security import decode_access_token
from .user_access import is_platform_admin

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _unauthorized() -> None:
    exc = api_error("invalid_authentication_credentials", status.HTTP_401_UNAUTHORIZED)
    exc.headers = {"WWW-Authenticate": "Bearer"}
    raise exc


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
    except Exception:
        _unauthorized()
    email = payload.get("sub")
    if not email:
        _unauthorized()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        exc = api_error("user_not_found", status.HTTP_401_UNAUTHORIZED)
        exc.headers = {"WWW-Authenticate": "Bearer"}
        raise exc
    if not token_version_matches(user, payload):
        _unauthorized()
    return user


def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not is_platform_admin(current_user):
        raise api_error("requires_administrative_privileges", status.HTTP_403_FORBIDDEN)
    return current_user
