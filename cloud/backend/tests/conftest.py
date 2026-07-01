"""Shared fixtures for cloud backend tests (CI path-scoping verification)."""

from __future__ import annotations

import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parents[1]
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))
_repo_root = Path(__file__).resolve().parents[3]
_shared_pkg = _repo_root / "packages" / "vendiqo_shared"
if _shared_pkg.is_dir() and str(_shared_pkg) not in sys.path:
    sys.path.insert(0, str(_shared_pkg))

from collections.abc import Generator

import pytest
from app.database import Base, apply_schema_patches, engine
from app.main import app
from app.rate_limit import limiter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _reset_rate_limiter() -> None:
    try:
        limiter._storage.reset()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _fresh_db() -> Generator[None, None, None]:
    """Isolated SQLite schema and rate-limit quota per test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    _reset_rate_limiter()
    yield
    _reset_rate_limiter()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def memory_db_session() -> Generator[Session, None, None]:
    """Separate in-memory DB for unit tests that must not touch the app engine."""
    local_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=local_engine)
    SessionLocal = sessionmaker(bind=local_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_token(client: TestClient) -> callable:
    def _token_for(email: str, password: str) -> str:
        r = client.post("/auth/token", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    return _token_for
