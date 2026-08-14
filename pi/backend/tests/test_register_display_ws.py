"""Register customer-display WebSocket push."""

from __future__ import annotations

import pytest
from tests.fixtures_bundles import bundle_copy, cash_register_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture
def bundle():
    return bundle_copy(cash_register_bundle())


@pytest.fixture
def client(client_session):
    return client_session


def test_display_ws_sends_snapshot_on_connect(client):
    c, _ = client
    put = c.put(
        "/v1/registers/reg-1/display",
        json={
            "event_id": 1,
            "payload": {"state": "ordering", "total_cents": 900, "lines": [{"article_id": 20, "qty": 1}]},
        },
    )
    assert put.status_code == 200, put.text

    with c.websocket_connect("/v1/registers/reg-1/display/ws?event_id=1") as ws:
        msg = ws.receive_json()
        assert msg["cash_register_uuid"] == "reg-1"
        assert msg["event_id"] == 1
        assert msg["payload"]["total_cents"] == 900
        assert msg["payload"]["state"] == "ordering"
        assert msg.get("updated_at")


def test_display_ws_broadcasts_after_put(client):
    c, _ = client
    with c.websocket_connect("/v1/registers/reg-1/display/ws?event_id=1") as ws:
        initial = ws.receive_json()
        assert initial["payload"] == {} or initial["payload"].get("state") in (None, "idle")

        put = c.put(
            "/v1/registers/reg-1/display",
            json={
                "event_id": 1,
                "payload": {"state": "twint", "show_twint": True, "total_cents": 1250},
            },
        )
        assert put.status_code == 200, put.text

        msg = ws.receive_json()
        assert msg["payload"]["state"] == "twint"
        assert msg["payload"]["total_cents"] == 1250


def test_display_http_get_unchanged_with_ws(client):
    c, _ = client
    body = {
        "event_id": 1,
        "payload": {"state": "ordering", "total_cents": 500, "lines": [{"article_id": 20, "qty": 1}]},
    }
    assert c.put("/v1/registers/reg-1/display", json=body).status_code == 200
    get = c.get("/v1/registers/reg-1/display", params={"event_id": 1})
    assert get.status_code == 200
    assert get.json()["payload"]["total_cents"] == 500


def test_display_ws_empty_snapshot_when_no_row(client):
    c, _ = client
    with c.websocket_connect("/v1/registers/reg-1/display/ws?event_id=1") as ws:
        msg = ws.receive_json()
        assert msg["cash_register_uuid"] == "reg-1"
        assert msg["event_id"] == 1
        assert msg["payload"] == {}
        assert msg["updated_at"] is None
