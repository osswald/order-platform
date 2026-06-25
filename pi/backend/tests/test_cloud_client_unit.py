"""Cloud client config and HTTP helpers."""

import asyncio
from pathlib import Path

import httpx
import pytest
from app.cloud_client import CloudConfigError, _require_config, fetch_bundle


def _write_edge_env(tmp_path: Path, monkeypatch, **overrides) -> None:
    import app.edge_config as edge_config

    path = tmp_path / "edge.env"
    values = {
        "CLOUD_BASE_URL": "https://api.example.test",
        "EDGE_CLIENT_ID": "cid-1",
        "EDGE_SECRET": "sec-1",
    }
    values.update(overrides)
    path.write_text("\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8")
    monkeypatch.setattr(edge_config, "EDGE_CONFIG_FILE", path)


def test_require_config_raises_when_missing(monkeypatch, tmp_path):
    _write_edge_env(tmp_path, monkeypatch, EDGE_SECRET="")
    with pytest.raises(CloudConfigError) as exc:
        _require_config()
    assert "EDGE_SECRET" in exc.value.missing


def test_fetch_bundle_uses_edge_headers(monkeypatch, tmp_path):
    _write_edge_env(tmp_path, monkeypatch)
    captured: dict = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers=None, params=None):
            captured["url"] = url
            captured["headers"] = headers or {}
            request = httpx.Request("GET", url)
            return httpx.Response(200, request=request, json={"events": []})

    monkeypatch.setattr("app.cloud_client.httpx.AsyncClient", FakeAsyncClient)
    data = asyncio.run(fetch_bundle())
    assert data == {"events": []}
    assert captured["url"].endswith("/edge/v1/bundle")
    assert captured["headers"]["X-Edge-Client-Id"] == "cid-1"
    assert captured["headers"]["X-Edge-Secret"] == "sec-1"
