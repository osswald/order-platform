"""Security hardening: OpenAPI toggle and login rate limiting."""

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def _ensure_db_tables():
    Base.metadata.create_all(bind=engine)
    yield


client = TestClient(app)


def test_openapi_available_when_enabled_by_default():
    response = client.get("/openapi.json")
    assert response.status_code == 200


def test_login_rate_limit_returns_429():
    for _ in range(10):
        response = client.post(
            "/auth/token",
            data={"username": "nobody@example.com", "password": "wrong"},
        )
        assert response.status_code in (401, 429)

    blocked = client.post(
        "/auth/token",
        data={"username": "nobody@example.com", "password": "wrong"},
    )
    assert blocked.status_code == 429
