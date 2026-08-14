"""SumUp Solo reader management HTTP API."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import Event, EventCashRegister, HireCompany, Organisation, SumupReader, User
from app.roles import ROLE_MEMBER, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)

SUMUP_READER_ID = "rdr_3MSAFM23CK82VSTT4BN6RWSQ65"
REMOTE_READER_ID = "rdr_NEWREADER00ABCDEFGHIJKLMN"


def _seed_connected_org() -> tuple[int, int]:
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"SumUp Readers HC {uuid4().hex[:8]}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="SumUp Readers Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
            sumup_merchant_code="MK10CL2A",
            sumup_access_token="access_test",
            sumup_refresh_token="refresh_test",
            sumup_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            sumup_connected_at=datetime.now(UTC),
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email=f"sumup-readers-{uuid4().hex[:8]}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return org.id, hc.id
    finally:
        db.close()


def _auth_headers() -> dict[str, str]:
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.email.like("sumup-readers-%@test.local"))
            .order_by(User.id.desc())
            .first()
        )
        email = user.email
    finally:
        db.close()
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _member_headers(org_id: int) -> dict[str, str]:
    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        member = User(
            email=f"sumup-readers-member-{uuid4().hex[:8]}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        member.organisations = [org]
        db.add(member)
        db.commit()
        email = member.email
    finally:
        db.close()
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _seed_api_key_org() -> int:
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"SumUp API Key HC {uuid4().hex[:8]}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="SumUp API Key Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
            sumup_merchant_code="MKAPIKEY1",
            sumup_access_token="sup_sk_test",
            sumup_refresh_token=None,
            sumup_token_expires_at=None,
            sumup_connected_at=datetime.now(UTC),
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email=f"sumup-readers-{uuid4().hex[:8]}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return org.id
    finally:
        db.close()


@patch("app.routers.sumup_readers.sumup_client.create_reader")
def test_pair_reader_success(mock_create):
    org_id, _ = _seed_connected_org()
    mock_create.return_value = {
        "id": SUMUP_READER_ID,
        "name": "Front counter",
        "status": "paired",
    }

    r = client.post(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
        json={"pairing_code": "4WLFDSBF", "label": "Front counter"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sumup_reader_id"] == SUMUP_READER_ID
    assert body["label"] == "Front counter"
    assert body["status"] == "paired"
    mock_create.assert_called_once()


@patch("app.routers.sumup_readers.sumup_client.create_reader")
def test_pair_reader_works_with_api_key_connection(mock_create):
    org_id = _seed_api_key_org()
    mock_create.return_value = {
        "id": SUMUP_READER_ID,
        "name": "Bar",
        "status": "paired",
    }

    r = client.post(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
        json={"pairing_code": "4WLFDSBF", "label": "Bar"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["label"] == "Bar"
    mock_create.assert_called_once_with("sup_sk_test", "MKAPIKEY1", "4WLFDSBF", "Bar")


@patch("app.routers.sumup_readers.sumup_client.create_reader")
def test_pair_reader_normalizes_pairing_code(mock_create):
    org_id, _ = _seed_connected_org()
    mock_create.return_value = {
        "id": SUMUP_READER_ID,
        "name": "Front counter",
        "status": "paired",
    }

    r = client.post(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
        json={"pairing_code": " 4wlf-dsbf ", "label": "Front counter"},
    )
    assert r.status_code == 201, r.text
    mock_create.assert_called_once()
    assert mock_create.call_args.args[2] == "4WLFDSBF"


@patch("app.routers.sumup_readers.sumup_client.create_reader")
def test_pair_reader_surfaces_sumup_pairing_error(mock_create):
    from app.sumup_client import SumupApiError

    org_id, _ = _seed_connected_org()
    mock_create.side_effect = SumupApiError(
        404,
        '{"detail":"no pairing for code","error_code":"NOT_FOUND"}',
    )

    r = client.post(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
        json={"pairing_code": "4WLFDSBF", "label": "Front counter"},
    )
    assert r.status_code == 502, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "sumup_pairing_code_invalid"
    assert "Pairing-Code" in detail["message"] or "pairing code" in detail["message"].lower()


def test_pair_reader_requires_label():
    org_id, _ = _seed_connected_org()
    r = client.post(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
        json={"pairing_code": "4WLFDSBF", "label": ""},
    )
    assert r.status_code == 422, r.text


def test_list_readers():
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        db.add(
            SumupReader(
                organisation_id=org_id,
                sumup_reader_id=SUMUP_READER_ID,
                label="Bar",
                status="paired",
            )
        )
        db.commit()
    finally:
        db.close()

    with patch("app.routers.sumup_readers.sumup_client.list_readers") as mock_list:
        mock_list.return_value = [
            {"id": SUMUP_READER_ID, "name": "Bar", "status": "paired"},
        ]
        r = client.get(
            f"/sumup/organisations/{org_id}/readers",
            headers=_auth_headers(),
        )
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["label"] == "Bar"
    assert items[0]["sumup_reader_id"] == SUMUP_READER_ID
    assert items[0]["status"] == "paired"


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_refreshes_stale_status(mock_token, mock_list):
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        db.add(
            SumupReader(
                organisation_id=org_id,
                sumup_reader_id=SUMUP_READER_ID,
                label="Bar",
                status="processing",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_list.return_value = [
        {"id": SUMUP_READER_ID, "name": "Bar", "status": "paired"},
    ]
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()[0]["status"] == "paired"
    mock_list.assert_called_once()

    db = SessionLocal()
    try:
        stored = db.query(SumupReader).filter(SumupReader.sumup_reader_id == SUMUP_READER_ID).first()
        assert stored is not None
        assert stored.status == "paired"
    finally:
        db.close()


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_keeps_local_status_when_sumup_unavailable(mock_token, mock_list):
    from app.sumup_client import SumupApiError

    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        db.add(
            SumupReader(
                organisation_id=org_id,
                sumup_reader_id=SUMUP_READER_ID,
                label="Bar",
                status="processing",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_list.side_effect = SumupApiError(503, "unavailable")
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()[0]["status"] == "processing"


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_imports_remote_reader(mock_token, mock_list):
    org_id, _ = _seed_connected_org()
    mock_list.return_value = [
        {
            "id": REMOTE_READER_ID,
            "name": "Frontdesk",
            "status": "paired",
            "device": {"identifier": "U1DT3NA00-CN", "model": "solo"},
        }
    ]
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["sumup_reader_id"] == REMOTE_READER_ID
    assert items[0]["label"] == "Frontdesk"
    assert items[0]["status"] == "paired"
    assert items[0]["device_identifier"] == "U1DT3NA00-CN"
    assert items[0]["device_model"] == "solo"

    db = SessionLocal()
    try:
        stored = db.query(SumupReader).filter(SumupReader.sumup_reader_id == REMOTE_READER_ID).one()
        assert stored.label == "Frontdesk"
        assert stored.device_identifier == "U1DT3NA00-CN"
        assert stored.device_model == "solo"
    finally:
        db.close()


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_imports_label_from_serial_when_name_empty(mock_token, mock_list):
    org_id, _ = _seed_connected_org()
    mock_list.return_value = [
        {
            "id": REMOTE_READER_ID,
            "name": "  ",
            "status": "paired",
            "device": {"identifier": "U1DT3NA00-CN", "model": "solo"},
        }
    ]
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()[0]["label"] == "U1DT3NA00-CN"


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_preserves_existing_local_label(mock_token, mock_list):
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        db.add(
            SumupReader(
                organisation_id=org_id,
                sumup_reader_id=SUMUP_READER_ID,
                label="Bar local",
                status="paired",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_list.return_value = [
        {"id": SUMUP_READER_ID, "name": "SumUp name", "status": "paired"},
    ]
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()[0]["label"] == "Bar local"


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_prunes_ids_missing_from_sumup(mock_token, mock_list):
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        db.add(
            SumupReader(
                organisation_id=org_id,
                sumup_reader_id=SUMUP_READER_ID,
                label="Stale",
                status="paired",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_list.return_value = [
        {"id": REMOTE_READER_ID, "name": "Keep me", "status": "paired"},
    ]
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert [row["sumup_reader_id"] for row in items] == [REMOTE_READER_ID]

    db = SessionLocal()
    try:
        assert db.query(SumupReader).filter(SumupReader.sumup_reader_id == SUMUP_READER_ID).first() is None
    finally:
        db.close()


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_empty_items_prunes_all(mock_token, mock_list):
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        db.add(
            SumupReader(
                organisation_id=org_id,
                sumup_reader_id=SUMUP_READER_ID,
                label="Gone",
                status="paired",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_list.return_value = []
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json() == []


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_does_not_prune_when_list_malformed(mock_token, mock_list):
    from app.sumup_client import SumupApiError

    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        db.add(
            SumupReader(
                organisation_id=org_id,
                sumup_reader_id=SUMUP_READER_ID,
                label="Keep",
                status="paired",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_list.side_effect = SumupApiError(502, "SumUp reader list missing items")
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()[0]["sumup_reader_id"] == SUMUP_READER_ID


@patch("app.routers.sumup_readers.sumup_client.list_readers")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_list_readers_prune_clears_cash_register_binding(mock_token, mock_list):
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        db.add(
            SumupReader(
                organisation_id=org_id,
                sumup_reader_id=SUMUP_READER_ID,
                label="Bar",
                status="paired",
            )
        )
        now = datetime.now(UTC)
        event = Event(
            name="Fest",
            status="config",
            start=now,
            end=now,
            organisation_id=org_id,
        )
        db.add(event)
        db.flush()
        db.add(
            EventCashRegister(
                event_id=event.id,
                name="Hauptkasse",
                pickup_code_prefix="A",
                pin="0000",
                layout_uuid=str(uuid4()),
                sumup_reader_id=SUMUP_READER_ID,
            )
        )
        db.commit()
        event_id = event.id
    finally:
        db.close()

    mock_list.return_value = []
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json() == []

    db = SessionLocal()
    try:
        reg = db.query(EventCashRegister).filter(EventCashRegister.event_id == event_id).one()
        assert reg.sumup_reader_id is None
    finally:
        db.close()


@patch("app.routers.sumup_readers.sumup_client.update_reader")
def test_rename_reader(mock_update):
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        reader = SumupReader(
            organisation_id=org_id,
            sumup_reader_id=SUMUP_READER_ID,
            label="Bar",
            status="paired",
        )
        db.add(reader)
        db.commit()
        reader_id = reader.id
    finally:
        db.close()

    mock_update.return_value = {
        "id": SUMUP_READER_ID,
        "name": "Terrace",
        "status": "paired",
    }

    r = client.patch(
        f"/sumup/organisations/{org_id}/readers/{reader_id}",
        headers=_auth_headers(),
        json={"label": "Terrace"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["label"] == "Terrace"
    mock_update.assert_called_once()


@patch("app.routers.sumup_readers.sumup_client.delete_reader")
def test_unpair_reader(mock_delete):
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        reader = SumupReader(
            organisation_id=org_id,
            sumup_reader_id=SUMUP_READER_ID,
            label="Bar",
            status="paired",
        )
        db.add(reader)
        db.commit()
        reader_id = reader.id
    finally:
        db.close()

    r = client.delete(
        f"/sumup/organisations/{org_id}/readers/{reader_id}",
        headers=_auth_headers(),
    )
    assert r.status_code == 204, r.text
    mock_delete.assert_called_once()

    db = SessionLocal()
    try:
        assert db.query(SumupReader).filter(SumupReader.id == reader_id).first() is None
    finally:
        db.close()


@patch("app.routers.sumup_readers.sumup_client.get_reader_status")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_reader_telemetry_maps_sumup_status(mock_token, mock_status):
    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        reader = SumupReader(
            organisation_id=org_id,
            sumup_reader_id=SUMUP_READER_ID,
            label="Bar",
            status="paired",
            device_identifier="U1DT3NA00-CN",
            device_model="solo",
        )
        db.add(reader)
        db.commit()
        reader_id = reader.id
    finally:
        db.close()

    mock_status.return_value = {
        "data": {
            "battery_level": 10.5,
            "connection_type": "Wi-Fi",
            "firmware_version": "3.3.3.21",
            "last_activity": "2025-09-25T15:20:00Z",
            "state": "IDLE",
            "status": "ONLINE",
        }
    }
    r = client.get(
        f"/sumup/organisations/{org_id}/readers/{reader_id}/telemetry",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["telemetry_available"] is True
    assert body["device_identifier"] == "U1DT3NA00-CN"
    assert body["device_model"] == "solo"
    assert body["online_status"] == "ONLINE"
    assert body["battery_level"] == 10.5
    assert body["connection_type"] == "Wi-Fi"
    assert body["firmware_version"] == "3.3.3.21"
    assert body["last_activity"] == "2025-09-25T15:20:00Z"
    assert body["state"] == "IDLE"
    mock_status.assert_called_once()


def test_reader_telemetry_unknown_reader_404():
    org_id, _ = _seed_connected_org()
    r = client.get(
        f"/sumup/organisations/{org_id}/readers/999999/telemetry",
        headers=_auth_headers(),
    )
    assert r.status_code == 404, r.text


@patch("app.routers.sumup_readers.sumup_client.get_reader_status")
@patch("app.routers.sumup_readers.get_valid_access_token", return_value="access_test")
def test_reader_telemetry_degrades_when_sumup_unavailable(mock_token, mock_status):
    from app.sumup_client import SumupApiError

    org_id, _ = _seed_connected_org()
    db = SessionLocal()
    try:
        reader = SumupReader(
            organisation_id=org_id,
            sumup_reader_id=SUMUP_READER_ID,
            label="Bar",
            status="paired",
            device_identifier="U1DT3NA00-CN",
            device_model="solo",
        )
        db.add(reader)
        db.commit()
        reader_id = reader.id
    finally:
        db.close()

    mock_status.side_effect = SumupApiError(404, "not found")
    r = client.get(
        f"/sumup/organisations/{org_id}/readers/{reader_id}/telemetry",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["telemetry_available"] is False
    assert body["device_identifier"] == "U1DT3NA00-CN"
    assert body["device_model"] == "solo"
    assert body["online_status"] is None

    db = SessionLocal()
    try:
        assert db.query(SumupReader).filter(SumupReader.id == reader_id).first() is not None
    finally:
        db.close()


def test_readers_member_forbidden():
    org_id, _ = _seed_connected_org()
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_member_headers(org_id),
    )
    assert r.status_code == 403, r.text
