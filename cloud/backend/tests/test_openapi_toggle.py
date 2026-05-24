import importlib
import os

import pytest
from fastapi.testclient import TestClient


def test_openapi_disabled_when_env_false(monkeypatch):
    monkeypatch.setenv("ENABLE_OPENAPI", "false")
    import app.main as main_module

    importlib.reload(main_module)
    try:
        client = TestClient(main_module.app)
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/docs").status_code == 404
    finally:
        monkeypatch.delenv("ENABLE_OPENAPI", raising=False)
        importlib.reload(main_module)
