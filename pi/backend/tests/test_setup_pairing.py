"""Local headless setup pairing API."""

from pathlib import Path


def _isolate_edge_config(monkeypatch, tmp_path: Path) -> Path:
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)
    for key in ("CLOUD_BASE_URL", "EDGE_CLIENT_ID", "EDGE_SECRET"):
        monkeypatch.delenv(key, raising=False)
    return path


def test_setup_status_reports_unpaired(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)

    response = client.get("/v1/setup/status")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "setup_url": "http://192.168.192.10",
        "cloud_base_url": "https://api.vendiqo.ch",
        "edge_client_id": None,
    }


def test_setup_pair_writes_edge_config(client, monkeypatch, tmp_path):
    config_path = _isolate_edge_config(monkeypatch, tmp_path)

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "appliance_id": 42,
                "appliance_name": "apollo",
                "edge_client_id": "client-123",
                "edge_secret": "secret-456",
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.requests = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict):
            assert url == "https://api.vendiqo.ch/edge/v1/pair"
            assert json == {"pairing_code": "123-456", "device_name": "vendiqo-pi"}
            return FakeResponse()

    import app.routers.setup as setup_router

    monkeypatch.setattr(setup_router.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/v1/setup/pair",
        json={
            "cloud_base_url": "https://api.vendiqo.ch/",
            "pairing_code": "123-456",
            "device_name": "vendiqo-pi",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["configured"] is True
    assert response.json()["edge_client_id"] == "client-123"
    assert "EDGE_SECRET=secret-456" in config_path.read_text(encoding="utf-8")

    status = client.get("/v1/setup/status")
    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert status.json()["cloud_base_url"] == "https://api.vendiqo.ch"


def test_setup_pair_rejects_invalid_cloud_url(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)

    response = client.post(
        "/v1/setup/pair",
        json={
            "cloud_base_url": "api.vendiqo.ch",
            "pairing_code": "123456",
        },
    )

    assert response.status_code == 422

