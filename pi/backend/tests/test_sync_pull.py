"""Sync pull error handling and cloud gateway responses."""

from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest


def _isolate_edge_config(monkeypatch, tmp_path: Path) -> None:
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)
    path.write_text(
        "\n".join(
            [
                "CLOUD_BASE_URL=https://api.vendiqo.ch",
                "EDGE_CLIENT_ID=client-123",
                "EDGE_SECRET=secret-456",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_sync_pull_surfaces_cloud_http_status(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)

    class FakeResponse:
        status_code = 403
        text = "No active appliance lending for this device today"

        def json(self):
            return {"detail": self.text}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, headers: dict):
            request = httpx.Request("GET", url)
            response = httpx.Response(403, request=request, text=FakeResponse.text)
            raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    monkeypatch.setattr("app.cloud_client.httpx.AsyncClient", FakeAsyncClient)

    response = client.post("/v1/sync/pull")

    assert response.status_code == 403, response.text
    assert "lending" in str(response.json()).lower()


def test_sync_pull_cloud_unreachable_returns_502(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, headers: dict):
            raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))

    monkeypatch.setattr("app.cloud_client.httpx.AsyncClient", FakeAsyncClient)

    response = client.post("/v1/sync/pull")

    assert response.status_code == 502, response.text


def test_sync_pull_success_returns_event_count(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "app.routers.edge_sync.pull_and_restore",
        AsyncMock(return_value={"event_count": 2, "restore": None}),
    )

    response = client.post("/v1/sync/pull")

    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True, "event_count": 2}
