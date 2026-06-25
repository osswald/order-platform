"""Admin test prints: one station slip per configured station."""

import pytest
from tests.fixtures_bundles import bundle_copy, default_bundle, kitchen_monitor_bundle

pytestmark = pytest.mark.usefixtures("mock_printer_tcp")


@pytest.fixture
def bundle():
    return bundle_copy(kitchen_monitor_bundle())


def test_test_station_prints_one_per_station(client, mock_printer_tcp):
    response = client.post("/v1/printers/test-station-prints", json={"event_id": 1})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["event_id"] == 1
    assert data["printed"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2
    names = {r["station_name"] for r in data["results"]}
    assert names == {"Grill", "Bar"}
    for r in data["results"]:
        assert r["ok"] is True
        assert r["printer_host"] == "127.0.0.1"
        assert r["printer_port"] == 9100
    assert len(mock_printer_tcp) == 2


def test_test_station_prints_unknown_event(client):
    response = client.post("/v1/printers/test-station-prints", json={"event_id": 999})
    assert response.status_code == 404


def test_test_station_prints_no_stations(client_session):
    c, Session = client_session
    import json

    from app.models import SyncedBundle

    empty = bundle_copy(default_bundle())
    db = Session()
    try:
        row = db.query(SyncedBundle).filter(SyncedBundle.id == 1).first()
        row.json_body = json.dumps(empty)
        db.commit()
    finally:
        db.close()

    response = c.post("/v1/printers/test-station-prints", json={"event_id": 1})
    assert response.status_code == 422
