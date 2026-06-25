"""HTTP tests for POST /v1/sync/push."""

from pathlib import Path
from unittest.mock import AsyncMock


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


def test_sync_push_returns_sent_count(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "app.routers.edge_sync.push_outbox",
        AsyncMock(return_value={"sent": 3, "errors": []}),
    )

    response = client.post("/v1/sync/push")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sent"] == 3
    assert body["errors"] == []


def test_sync_push_empty_outbox_returns_zero_sent(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "app.routers.edge_sync.push_outbox",
        AsyncMock(return_value={"sent": 0, "errors": []}),
    )

    response = client.post("/v1/sync/push")

    assert response.status_code == 200, response.text
    assert response.json()["sent"] == 0
