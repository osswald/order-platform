"""SumUp Solo reader management HTTP API."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, SumupReader, User
from app.roles import ROLE_MEMBER, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)

SUMUP_READER_ID = "rdr_3MSAFM23CK82VSTT4BN6RWSQ65"


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

    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["label"] == "Bar"
    assert items[0]["sumup_reader_id"] == SUMUP_READER_ID


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


def test_readers_member_forbidden():
    org_id, _ = _seed_connected_org()
    r = client.get(
        f"/sumup/organisations/{org_id}/readers",
        headers=_member_headers(org_id),
    )
    assert r.status_code == 403, r.text
