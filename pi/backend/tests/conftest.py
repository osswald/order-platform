"""Shared test fixtures for pi backend."""

from __future__ import annotations

import json
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, apply_schema_patches
from app.main import app
from app.models import SyncedBundle
from tests.fixtures_bundles import bundle_copy, default_bundle


@dataclass
class ApiTestContext:
    client: TestClient
    Session: sessionmaker[Session]


@pytest.fixture
def bundle() -> dict:
    return bundle_copy(default_bundle())


@pytest.fixture
def print_to_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PRINT_TO_FILE", "1")
    monkeypatch.setenv("PRINT_OUTPUT_DIR", str(tmp_path))


@pytest.fixture
def isolated_engine() -> Generator[Engine, None, None]:
    """In-memory SQLite engine; replaces app.database.engine for the test."""
    import app.database as database

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    previous_engine = database.engine
    previous_session_local = database.SessionLocal
    database.engine = engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    try:
        yield engine
    finally:
        database.engine = previous_engine
        database.SessionLocal = previous_session_local
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
