from datetime import datetime, timedelta, timezone
import os
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from .env import is_production

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEV_DEFAULT_SECRET_KEY = "replace-me-with-secure-random-secret"
_MIN_PRODUCTION_SECRET_LEN = 32
_FORBIDDEN_PRODUCTION_SECRETS = frozenset(
    {
        DEV_DEFAULT_SECRET_KEY,
        "change-me-to-a-long-random-string",
        "change-me",
        "devsecretkey123456789",
    }
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def load_secret_key() -> str:
    """Resolve JWT signing secret. Production requires a strong explicit SECRET_KEY."""
    raw = os.getenv("SECRET_KEY")
    if is_production():
        if not raw:
            raise RuntimeError(
                "SECRET_KEY must be set when APP_ENV=production "
                "(use a long random string, e.g. openssl rand -hex 32)"
            )
        key = raw.strip()
        if key in _FORBIDDEN_PRODUCTION_SECRETS:
            raise RuntimeError(
                "SECRET_KEY is a known placeholder and cannot be used in production"
            )
        if len(key) < _MIN_PRODUCTION_SECRET_LEN:
            raise RuntimeError(
                f"SECRET_KEY must be at least {_MIN_PRODUCTION_SECRET_LEN} characters in production"
            )
        return key
    return (raw or DEV_DEFAULT_SECRET_KEY).strip()


SECRET_KEY = load_secret_key()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _encode_token(
    data: dict[str, Any],
    token_type: str,
    expires_delta: timedelta,
) -> str:
    to_encode = {k: v for k, v in data.items() if k not in ("typ", "exp")}
    expire = _utcnow() + expires_delta
    to_encode.update({"exp": expire, "typ": token_type})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise
    if payload.get("typ") != expected_type:
        raise JWTError("Invalid token type")
    return payload


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    delta = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return _encode_token(data, TOKEN_TYPE_ACCESS, delta)


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode_token(token, TOKEN_TYPE_ACCESS)


def create_refresh_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    delta = expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return _encode_token(data, TOKEN_TYPE_REFRESH, delta)


def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode_token(token, TOKEN_TYPE_REFRESH)
