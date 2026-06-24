"""Shared database session helpers."""

from collections.abc import Callable
from typing import NoReturn

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def commit_or_raise(
    db: Session,
    *,
    on_integrity: Callable[[], NoReturn] | None = None,
) -> None:
    """Commit the session; roll back and optionally map IntegrityError."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if on_integrity is not None:
            on_integrity()
        raise
