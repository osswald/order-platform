"""Regression tests for commit_or_raise."""

from unittest.mock import MagicMock

import pytest
from app.db_errors import commit_or_raise
from sqlalchemy.exc import IntegrityError


def test_commit_or_raise_commits_on_success():
    db = MagicMock()
    commit_or_raise(db)
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_commit_or_raise_rollback_and_maps_integrity():
    db = MagicMock()
    db.commit.side_effect = IntegrityError("INSERT", {}, Exception("dup"))

    def on_integrity() -> None:
        raise ValueError("duplicate key mapped")

    with pytest.raises(ValueError, match="duplicate key mapped"):
        commit_or_raise(db, on_integrity=on_integrity)
    db.rollback.assert_called_once()


def test_commit_or_raise_reraises_integrity_without_handler():
    db = MagicMock()
    err = IntegrityError("INSERT", {}, Exception("dup"))
    db.commit.side_effect = err

    with pytest.raises(IntegrityError):
        commit_or_raise(db)
    db.rollback.assert_called_once()
