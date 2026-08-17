"""SumUp reader checkout edge HTTP API."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    Event,
    HireCompany,
    Organisation,
    SumupCheckout,
    SumupReader,
)
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import add_lending, country_id_by_code

client = TestClient(app)

READER_ID = "rdr_test1234567890123456789012"
CHECKOUT_ID = "co_test_checkout_001"
TRANSACTION_ID = "410fc44a-5956-44e1-b5cc-19c6f8d727a4"


def _edge_sumup_fixture(
    *,
    payment_types: list[str] | None = None,
    connected: bool = True,
) -> tuple[dict[str, str], int]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"SumUp Edge HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"SumUp Edge Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        if connected:
            org.sumup_merchant_code = "MK10CL2A"
            org.sumup_access_token = "access_test"
            org.sumup_refresh_token = "refresh_test"
            org.sumup_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
            org.sumup_connected_at = datetime.now(UTC)
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        ev = Event(
            name="Live",
            status="prod",
            start=now - timedelta(hours=1),
            end=now + timedelta(days=1),
            organisation_id=org.id,
            payment_types=payment_types or ["cash", "sumup_connected"],
        )
        db.add(ev)
        db.flush()
        if connected:
            db.add(
                SumupReader(
                    organisation_id=org.id,
                    sumup_reader_id=READER_ID,
                    label="Bar",
                    status="paired",
                )
            )
        appliance = Appliance(hire_company_id=hc.id, type="server", name="Pi")
        db.add(appliance)
        db.flush()
        today = now.date()
        add_lending(
            db,
            appliance_id=appliance.id,
            organisation_id=org.id,
            start_date=today,
            end_date=today,
            returned_at=None,
        )
        secret = f"secret-{suffix}"
        cred = ApplianceEdgeCredential(
            appliance_id=appliance.id,
            edge_client_id=f"cid-{suffix}",
            edge_secret_hash=get_password_hash(secret),
            status="active",
        )
        db.add(cred)
        db.commit()
        return (
            {
                "X-Edge-Client-Id": cred.edge_client_id,
                "X-Edge-Secret": secret,
            },
            ev.id,
        )
    finally:
        db.close()


@patch("app.routers.sumup_edge.get_valid_access_token", return_value="access_test")
@patch("app.routers.sumup_edge.sumup_client.create_reader_checkout")
def test_sumup_create_checkout(mock_create_checkout, _mock_token):
    headers, event_id = _edge_sumup_fixture()
    mock_create_checkout.return_value = {
        "data": {
            "checkout_id": CHECKOUT_ID,
            "client_transaction_id": TRANSACTION_ID,
        }
    }

    r = client.post(
        "/edge/v1/sumup/checkout",
        headers=headers,
        json={
            "event_id": event_id,
            "amount_cents": 500,
            "currency": "CHF",
            "reader_id": READER_ID,
            "client_order_id": "order-abc",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["checkout_id"] == CHECKOUT_ID
    assert body["status"] == "pending"
    assert body["transaction_id"] == TRANSACTION_ID
    mock_create_checkout.assert_called_once()
    kwargs = mock_create_checkout.call_args.kwargs
    assert kwargs["amount_cents"] == 500
    assert kwargs["foreign_transaction_id"] == "order-abc"
    assert "affiliate" not in str(mock_create_checkout.call_args)


def test_sumup_checkout_requires_sumup_connected_event():
    headers, event_id = _edge_sumup_fixture(payment_types=["cash"])
    r = client.post(
        "/edge/v1/sumup/checkout",
        headers=headers,
        json={
            "event_id": event_id,
            "amount_cents": 500,
            "currency": "CHF",
            "reader_id": READER_ID,
        },
    )
    assert r.status_code == 403, r.text


def test_sumup_checkout_requires_connected_org():
    headers, event_id = _edge_sumup_fixture(connected=False)
    r = client.post(
        "/edge/v1/sumup/checkout",
        headers=headers,
        json={
            "event_id": event_id,
            "amount_cents": 500,
            "currency": "CHF",
            "reader_id": READER_ID,
        },
    )
    assert r.status_code == 409, r.text


def test_sumup_checkout_rejects_unknown_reader():
    headers, event_id = _edge_sumup_fixture()
    r = client.post(
        "/edge/v1/sumup/checkout",
        headers=headers,
        json={
            "event_id": event_id,
            "amount_cents": 500,
            "currency": "CHF",
            "reader_id": "rdr_unknown",
        },
    )
    assert r.status_code == 404, r.text


@patch("app.routers.sumup_edge.get_valid_access_token", return_value="access_test")
@patch("app.routers.sumup_edge.sumup_client.terminate_checkout")
def test_sumup_terminate_checkout(mock_terminate, _mock_token):
    headers, event_id = _edge_sumup_fixture()
    mock_terminate.return_value = {}

    r = client.post(
        "/edge/v1/sumup/terminate",
        headers=headers,
        json={"event_id": event_id, "reader_id": READER_ID},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    mock_terminate.assert_called_once()


@patch("app.routers.sumup_edge.get_valid_access_token", return_value="access_test")
@patch("app.sumup_receipt_fetch.sumup_client.get_transaction")
@patch("app.routers.sumup_edge.sumup_client.get_reader_checkout")
def test_sumup_checkout_status_paid(mock_get_checkout, mock_get_transaction, _mock_token):
    headers, event_id = _edge_sumup_fixture()
    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.sumup_merchant_code == "MK10CL2A").order_by(Organisation.id.desc()).first()
        db.add(
            SumupCheckout(
                organisation_id=org.id,
                event_id=event_id,
                sumup_reader_id=READER_ID,
                sumup_checkout_id=CHECKOUT_ID,
                amount_cents=500,
                currency="CHF",
                status="pending",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_get_checkout.return_value = {
        "data": {
            "checkout_id": CHECKOUT_ID,
            "client_transaction_id": TRANSACTION_ID,
            "status": "successful",
        }
    }
    mock_get_transaction.return_value = {
        "id": TRANSACTION_ID,
        "transaction_code": "TEENSK4W2K",
        "auth_code": "053201",
        "entry_mode": "CONTACTLESS",
        "card": {"last_4_digits": "3456", "type": "MASTERCARD"},
    }

    r = client.get(
        f"/edge/v1/sumup/status?event_id={event_id}&checkout_id={CHECKOUT_ID}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "paid"
    assert body["transaction_id"] == TRANSACTION_ID
    assert body["receipt_info"] == {
        "transaction_code": "TEENSK4W2K",
        "auth_code": "053201",
        "card_last_4": "3456",
        "card_type": "MASTERCARD",
        "entry_mode": "CONTACTLESS",
        "timestamp": None,
        "merchant_code": None,
    }
    mock_get_checkout.assert_called_once_with("access_test", "MK10CL2A", READER_ID, CHECKOUT_ID)
    mock_get_transaction.assert_called()

    db = SessionLocal()
    try:
        row = db.query(SumupCheckout).filter(SumupCheckout.sumup_checkout_id == CHECKOUT_ID).first()
        assert row is not None
        assert row.receipt_info_json["transaction_code"] == "TEENSK4W2K"
        assert row.receipt_info_json["card_last_4"] == "3456"
    finally:
        db.close()


@patch("app.routers.sumup_edge.get_valid_access_token", return_value="access_test")
@patch("app.sumup_receipt_fetch.sumup_client.get_transaction")
@patch("app.routers.sumup_edge.sumup_client.get_reader_checkout")
def test_sumup_checkout_status_paid_survives_receipt_fetch_failure(
    mock_get_checkout, mock_get_transaction, _mock_token
):
    headers, event_id = _edge_sumup_fixture()
    db = SessionLocal()
    try:
        org = (
            db.query(Organisation)
            .filter(Organisation.sumup_merchant_code == "MK10CL2A")
            .order_by(Organisation.id.desc())
            .first()
        )
        db.add(
            SumupCheckout(
                organisation_id=org.id,
                event_id=event_id,
                sumup_reader_id=READER_ID,
                sumup_checkout_id=CHECKOUT_ID,
                amount_cents=500,
                currency="CHF",
                status="pending",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_get_checkout.return_value = {
        "data": {
            "checkout_id": CHECKOUT_ID,
            "client_transaction_id": TRANSACTION_ID,
            "status": "successful",
        }
    }
    from app.sumup_client import SumupApiError

    mock_get_transaction.side_effect = SumupApiError(404, "not found")

    r = client.get(
        f"/edge/v1/sumup/status?event_id={event_id}&checkout_id={CHECKOUT_ID}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "paid"
    assert body["transaction_id"] == TRANSACTION_ID
    assert body["receipt_info"] is None


@patch("app.routers.sumup_edge.get_valid_access_token", return_value="access_test")
@patch("app.routers.sumup_edge.sumup_client.get_reader_checkout")
def test_sumup_checkout_status_expires_stale_pending(mock_get_checkout, _mock_token):
    headers, event_id = _edge_sumup_fixture()
    db = SessionLocal()
    try:
        org = (
            db.query(Organisation)
            .filter(Organisation.sumup_merchant_code == "MK10CL2A")
            .order_by(Organisation.id.desc())
            .first()
        )
        db.add(
            SumupCheckout(
                organisation_id=org.id,
                event_id=event_id,
                sumup_reader_id=READER_ID,
                sumup_checkout_id=CHECKOUT_ID,
                amount_cents=500,
                currency="CHF",
                status="pending",
            )
        )
        db.commit()
    finally:
        db.close()

    mock_get_checkout.return_value = {
        "data": {
            "checkout_id": CHECKOUT_ID,
            "client_transaction_id": TRANSACTION_ID,
            "status": "pending",
            "payment_status": None,
            "valid_until": "2020-01-01T00:00:00Z",
        }
    }

    r = client.get(
        f"/edge/v1/sumup/status?event_id={event_id}&checkout_id={CHECKOUT_ID}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "terminated"
    assert body["transaction_id"] == TRANSACTION_ID


def test_sumup_webhook_marks_checkout_paid(monkeypatch):
    monkeypatch.setenv("SUMUP_WEBHOOK_SECRET", "whsec_test")
    headers, event_id = _edge_sumup_fixture()
    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.sumup_merchant_code == "MK10CL2A").order_by(Organisation.id.desc()).first()
        db.add(
            SumupCheckout(
                organisation_id=org.id,
                event_id=event_id,
                sumup_reader_id=READER_ID,
                sumup_checkout_id=CHECKOUT_ID,
                amount_cents=500,
                currency="CHF",
                status="pending",
            )
        )
        db.commit()
    finally:
        db.close()

    payload = {
        "event_type": "checkout.status.updated",
        "id": "evt_sumup_1",
        "checkout_id": CHECKOUT_ID,
        "status": "PAID",
        "transaction_id": TRANSACTION_ID,
    }
    r = client.post(
        "/sumup/webhooks",
        headers={"X-SumUp-Webhook-Secret": "whsec_test"},
        json=payload,
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        row = db.query(SumupCheckout).filter(SumupCheckout.sumup_checkout_id == CHECKOUT_ID).first()
        assert row is not None
        assert row.status == "paid"
        assert row.sumup_transaction_id == TRANSACTION_ID
    finally:
        db.close()
