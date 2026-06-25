"""Shared test fixtures for pi backend."""

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

import json
from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import patch

import pytest
from app import models, models_operational  # noqa: F401
from app.database import Base, init_test_schema
from app.main import app
from app.models import SyncedBundle
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from tests.fixtures_bundles import bundle_copy, default_bundle


@dataclass
class ApiTestContext:
    client: TestClient
    Session: sessionmaker[Session]


@pytest.fixture
def bundle() -> dict:
    return bundle_copy(default_bundle())


@pytest.fixture
def mock_printer_tcp(monkeypatch):
    """Mock TCP ESC/POS sends so tests do not need a physical or emulated printer."""
    calls: list[tuple[str, int]] = []

    class MockWriter:
        def write(self, data: bytes) -> None:
            return None

        def close(self) -> None:
            return None

        async def drain(self) -> None:
            return None

        async def wait_closed(self) -> None:
            return None

    class MockReader:
        pass

    async def fake_open_connection(host, port):
        calls.append((str(host), int(port)))
        return MockReader(), MockWriter()

    monkeypatch.setattr("app.print_worker.asyncio.open_connection", fake_open_connection)
    return calls


@pytest.fixture
def isolated_engine() -> Generator[Engine, None, None]:
    """In-memory SQLite engine; replaces app.database.engine for the test."""
    import app.database as database

    engine = create_engine(
        "sqlite:///?cache=shared",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    previous_engine = database.engine
    previous_session_local = database.SessionLocal
    database.engine = engine
    new_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.SessionLocal = new_session_local
    import app.print_worker as print_worker
    import app.sync_worker as sync_worker

    previous_print_session = print_worker.SessionLocal
    previous_sync_session = sync_worker.SessionLocal
    print_worker.SessionLocal = new_session_local
    sync_worker.SessionLocal = new_session_local
    Base.metadata.drop_all(bind=engine)
    init_test_schema()
    try:
        yield engine
    finally:
        database.engine = previous_engine
        database.SessionLocal = previous_session_local
        print_worker.SessionLocal = previous_print_session
        sync_worker.SessionLocal = previous_sync_session
        app.dependency_overrides.clear()


@pytest.fixture
def db_session(isolated_engine) -> Generator[Session, None, None]:
    session = sessionmaker(autocommit=False, autoflush=False, bind=isolated_engine)()
    try:
        yield session
    finally:
        session.close()


def _seed_bundle(Session: sessionmaker[Session], bundle: dict) -> None:
    db = Session()
    try:
        db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
        db.commit()
    finally:
        db.close()


@pytest.fixture
def api_context(isolated_engine, bundle) -> Generator[ApiTestContext, None, None]:
    import app.database as database
    from app.routers import edge_api

    Session = database.SessionLocal
    _seed_bundle(Session, bundle)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[edge_api.get_db] = override_get_db
    with patch("app.main.run_migrations"), patch("app.main.ensure_default_synced_bundle"):
        with TestClient(app) as test_client:
            yield ApiTestContext(client=test_client, Session=Session)
    app.dependency_overrides.clear()


@pytest.fixture
def client(api_context) -> TestClient:
    """FastAPI test client with seeded bundle (module may override ``bundle``)."""
    return api_context.client


@pytest.fixture
def client_session(api_context) -> tuple[TestClient, sessionmaker[Session]]:
    """Test client and SQLAlchemy session factory for direct DB assertions."""
    return api_context.client, api_context.Session
