"""Local headless setup pairing API."""

from pathlib import Path


def _isolate_edge_config(monkeypatch, tmp_path: Path) -> Path:
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)
    for key in ("CLOUD_BASE_URL", "EDGE_CLIENT_ID", "EDGE_SECRET"):
        monkeypatch.delenv(key, raising=False)
    return path


def _status_defaults(**overrides):
    base = {
        "configured": False,
        "setup_url": "http://192.168.192.10",
        "cloud_base_url": "https://api.vendiqo.ch",
        "edge_client_id": None,
        "can_unpair": False,
        "emulated_printer": False,
    }
    base.update(overrides)
    return base


def test_setup_status_reports_unpaired(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)

    response = client.get("/v1/setup/status")

    assert response.status_code == 200
    assert response.json() == _status_defaults()


def test_setup_pair_writes_edge_config(client, monkeypatch, tmp_path):
    config_path = _isolate_edge_config(monkeypatch, tmp_path)
    cloud_bundle = {
        "organisation_id": 7,
        "events": [{"id": 42, "name": "Cloud Event", "configuration": {}}],
    }

    class FakeResponse:
        def __init__(self, payload: dict):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

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
            return FakeResponse({
                "appliance_id": 42,
                "appliance_name": "apollo",
                "edge_client_id": "client-123",
                "edge_secret": "secret-456",
            })

        async def get(self, url: str, headers: dict):
            assert url == "https://api.vendiqo.ch/edge/v1/bundle"
            assert headers == {
                "X-Edge-Client-Id": "client-123",
                "X-Edge-Secret": "secret-456",
            }
            return FakeResponse(cloud_bundle)

    import app.routers.setup as setup_router

    monkeypatch.setattr(setup_router.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/v1/setup/pair",
        json={
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

    sync_status = client.get("/v1/sync/status")
    assert sync_status.status_code == 200
    assert sync_status.json()["configured"] is True

    sync_pull = client.post("/v1/sync/pull")
    assert sync_pull.status_code == 200, sync_pull.text
    assert sync_pull.json()["event_count"] == 1

    bundle = client.get("/v1/bundle")
    assert bundle.status_code == 200
    assert bundle.json()["organisation_id"] == 7


def test_setup_pair_uses_default_cloud_base_url(client, monkeypatch, tmp_path):
    _isolate_edge_config(monkeypatch, tmp_path)
    seen_urls: list[str] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "appliance_id": 1,
                "edge_client_id": "c1",
                "edge_secret": "s1",
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict):
            seen_urls.append(url)
            return FakeResponse()

    import app.routers.setup as setup_router

    monkeypatch.setattr(setup_router.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/v1/setup/pair",
        json={
            "pairing_code": "123-456",
        },
    )

    assert response.status_code == 200, response.text
    assert seen_urls == ["https://api.vendiqo.ch/edge/v1/pair"]


def test_setup_pair_blocked_when_already_configured(client, monkeypatch, tmp_path):
    config_path = _isolate_edge_config(monkeypatch, tmp_path)
    config_path.write_text(
        "CLOUD_BASE_URL=https://api.vendiqo.ch\n"
        "EDGE_CLIENT_ID=existing\n"
        "EDGE_SECRET=secret\n",
        encoding="utf-8",
    )

    response = client.post(
        "/v1/setup/pair",
        json={"pairing_code": "123-456"},
    )

    assert response.status_code == 403
    assert "already paired" in response.json()["detail"].lower()


def test_setup_unpair_requires_secret(client, monkeypatch, tmp_path):
    config_path = _isolate_edge_config(monkeypatch, tmp_path)
    config_path.write_text(
        "CLOUD_BASE_URL=https://api.vendiqo.ch\n"
        "EDGE_CLIENT_ID=existing\n"
        "EDGE_SECRET=secret\n",
        encoding="utf-8",
    )

    response = client.post("/v1/setup/unpair", json={"unpair_secret": "nope"})
    assert response.status_code == 403


def test_setup_unpair_clears_config(client, monkeypatch, tmp_path):
    config_path = _isolate_edge_config(monkeypatch, tmp_path)
    config_path.write_text(
        "CLOUD_BASE_URL=https://api.vendiqo.ch\n"
        "EDGE_CLIENT_ID=existing\n"
        "EDGE_SECRET=secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PI_SETUP_UNPAIR_SECRET", "factory-reset")
    import app.routers.setup as setup_router

    async def fake_cloud_unpair():
        return {"status": "revoked"}

    monkeypatch.setattr(setup_router, "unpair_device", fake_cloud_unpair)

    response = client.post(
        "/v1/setup/unpair",
        json={"unpair_secret": "factory-reset"},
    )

    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert not config_path.exists()


def test_setup_unpair_keeps_local_config_when_cloud_revoke_fails(client, monkeypatch, tmp_path):
    config_path = _isolate_edge_config(monkeypatch, tmp_path)
    config_path.write_text(
        "CLOUD_BASE_URL=https://api.vendiqo.ch\n"
        "EDGE_CLIENT_ID=existing\n"
        "EDGE_SECRET=secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PI_SETUP_UNPAIR_SECRET", "factory-reset")
    import app.routers.setup as setup_router
    from app.cloud_client import CloudRequestError

    async def fake_cloud_unpair():
        raise CloudRequestError(502, "upstream down")

    monkeypatch.setattr(setup_router, "unpair_device", fake_cloud_unpair)

    response = client.post(
        "/v1/setup/unpair",
        json={"unpair_secret": "factory-reset"},
    )

    assert response.status_code == 502
    assert "local unpair cancelled" in response.json()["detail"].lower()
    assert config_path.exists()
