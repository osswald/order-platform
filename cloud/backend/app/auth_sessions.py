"""Session invalidation via per-user token version (security #9)."""

from sqlalchemy.orm import Session

from .models import User

TOKEN_VERSION_CLAIM = "tv"


def session_claims(user: User) -> dict[str, str | int]:
    return {"sub": user.email, TOKEN_VERSION_CLAIM: int(user.token_version or 0)}


def token_version_matches(user: User, payload: dict) -> bool:
    claim = payload.get(TOKEN_VERSION_CLAIM)
    if claim is None:
        return False
    return int(claim) == int(user.token_version or 0)


def invalidate_user_sessions(user: User, db: Session) -> int:
    user.token_version = int(user.token_version or 0) + 1
    db.commit()
    db.refresh(user)
    return user.token_version
