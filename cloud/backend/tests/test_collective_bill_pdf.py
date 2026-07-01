"""Collective bill PDF document and route tests."""

from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from app.database import Base, SessionLocal
from app.event_collective_bills import build_single_collective_bill, upsert_collective_bill_from_payload
from app.main import app
from app.models import (
    Appliance,
    EdgeSubmittedOrder,
    Event,
    HireCompany,
    Organisation,
    User,
)
from app.pdf.documents.collective_bill import build_collective_bill_pdf
from app.roles import ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country

client = TestClient(app)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch_country_id = ensure_country(db, "CH", country_id=1)
    hc = HireCompany(id=1, name="HC")
    db.add(hc)
    org = Organisation(
        id=1,
        hire_company_id=1,
        name="PDF Org",
        address="Testweg 1",
        zip="8000",
        city="Zürich",
        country_id=ch_country_id,
        currency="CHF",
    )
    db.add(org)
    now = datetime.now(UTC)
    ev = Event(
        id=1,
        name="PDF Fest",
        status="active",
        start=now,
        end=now,
        organisation_id=1,
        payment_mode="pay_later",
    )
    db.add(ev)
    app_row = Appliance(id=1, hire_company_id=1, type="pi", name="Pi")
    db.add(app_row)
    db.commit()
    yield db, ev, org
    db.close()


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _seed_collective_bill(db, event, *, bill_uuid: str = "cb-pdf-1") -> None:
    payload = {
        "collective_bill_uuid": bill_uuid,
        "collective_bill_name": "Personal",
        "payment_status": "paid",
        "order_number": 42,
        "ordered_at": "2026-03-01T12:00:00+00:00",
        "lines": [
            {
                "article_id": 1,
                "qty": 2,
                "unit_cents": 500,
                "note": "Ohne Eis",
                "additions": [],
            }
        ],
        "payments": [{"type": "cash", "amount_cents": 1000, "paid_at": "2026-03-01T12:05:00+00:00"}],
    }
    upsert_collective_bill_from_payload(db, event_id=event.id, appliance_id=1, payload=payload)
    db.add(
        EdgeSubmittedOrder(
            client_order_id="order-pdf-1",
            appliance_id=1,
            organisation_id=event.organisation_id,
            event_id=event.id,
            payload=payload,
        )
    )
    db.commit()


def test_build_collective_bill_pdf_content(db_session):
    db, event, org = db_session
    _seed_collective_bill(db, event)
    bill = build_single_collective_bill(db, event, "cb-pdf-1")
    assert bill is not None
    pdf_bytes = build_collective_bill_pdf(
        event=event,
        organisation=org,
        bill=bill,
        currency="CHF",
        locale="de",
    )
    assert pdf_bytes.startswith(b"%PDF")
    text = _pdf_text(pdf_bytes)
    assert "Sammelrechnung" in text
    assert "PDF Org" in text
    assert "Personal" in text
    assert "PDF Fest" in text
    assert "5.00 CHF" in text or "5.00" in text
    assert "10.00 CHF" in text or "10.00" in text
    assert "Ohne Eis" in text
    assert "Bemerkung" not in text
    assert text.count("Total") >= 2
    assert "10.00 CHF" in text or "10.00" in text


def test_build_collective_bill_pdf_section_totals_multi_order(db_session):
    db, event, org = db_session
    for idx, (client_id, order_no, cents) in enumerate(
        (
            ("order-a", 1, 500),
            ("order-b", 2, 300),
        ),
        start=1,
    ):
        payload = {
            "collective_bill_uuid": "cb-pdf-multi",
            "collective_bill_name": "Tisch",
            "payment_status": "open",
            "order_number": order_no,
            "client_order_id": client_id,
            "lines": [{"article_id": idx, "qty": 1, "unit_cents": cents, "additions": []}],
        }
        upsert_collective_bill_from_payload(db, event_id=event.id, appliance_id=1, payload=payload)
        db.add(
            EdgeSubmittedOrder(
                client_order_id=client_id,
                appliance_id=1,
                organisation_id=event.organisation_id,
                event_id=event.id,
                payload=payload,
            )
        )
    db.commit()
    bill = build_single_collective_bill(db, event, "cb-pdf-multi")
    pdf_bytes = build_collective_bill_pdf(
        event=event,
        organisation=org,
        bill=bill,
        currency="CHF",
        locale="de",
    )
    text = _pdf_text(pdf_bytes)
    assert text.count("Total") >= 3
    assert "8.00 CHF" in text or "8.00" in text
    assert "5.00 CHF" in text or "5.00" in text
    assert "3.00 CHF" in text or "3.00" in text


def test_build_collective_bill_pdf_paid_without_payment_details(db_session):
    db, event, org = db_session
    payload = {
        "collective_bill_uuid": "cb-pdf-paid",
        "collective_bill_name": "Personal",
        "payment_status": "paid",
        "lines": [{"article_id": 1, "qty": 1, "unit_cents": 500, "additions": []}],
    }
    upsert_collective_bill_from_payload(db, event_id=event.id, appliance_id=1, payload=payload)
    db.add(
        EdgeSubmittedOrder(
            client_order_id="order-pdf-paid",
            appliance_id=1,
            organisation_id=event.organisation_id,
            event_id=event.id,
            payload=payload,
        )
    )
    db.commit()
    bill = build_single_collective_bill(db, event, "cb-pdf-paid")
    pdf_bytes = build_collective_bill_pdf(
        event=event,
        organisation=org,
        bill=bill,
        currency="CHF",
        locale="de",
    )
    text = _pdf_text(pdf_bytes)
    assert "Keine Zahlungen erfasst" not in text
    assert "Einzelzahlungen nicht synchronisiert" in text


def test_build_collective_bill_pdf_note_with_addition(db_session):
    db, event, org = db_session
    payload = {
        "collective_bill_uuid": "cb-pdf-2",
        "collective_bill_name": "Bar",
        "payment_status": "open",
        "order_number": 7,
        "lines": [
            {
                "article_id": 1,
                "qty": 1,
                "unit_cents": 600,
                "note": "Extra scharf",
                "additions": [{"article_id": 2, "name": "Gross", "qty": 1}],
            }
        ],
    }
    upsert_collective_bill_from_payload(db, event_id=event.id, appliance_id=1, payload=payload)
    db.add(
        EdgeSubmittedOrder(
            client_order_id="order-pdf-2",
            appliance_id=1,
            organisation_id=event.organisation_id,
            event_id=event.id,
            payload=payload,
        )
    )
    db.commit()
    bill = build_single_collective_bill(db, event, "cb-pdf-2")
    pdf_bytes = build_collective_bill_pdf(
        event=event,
        organisation=org,
        bill=bill,
        currency="CHF",
        locale="de",
    )
    text = _pdf_text(pdf_bytes)
    assert "Gross" in text
    assert "Extra scharf" in text
    assert "Bemerkung" not in text


def test_build_collective_bill_pdf_locale_en(db_session):
    db, event, org = db_session
    _seed_collective_bill(db, event)
    bill = build_single_collective_bill(db, event, "cb-pdf-1")
    pdf_bytes = build_collective_bill_pdf(
        event=event,
        organisation=org,
        bill=bill,
        currency="CHF",
        locale="en",
    )
    text = _pdf_text(pdf_bytes)
    assert "Collective bill" in text
    assert "For: Personal" in text


def test_build_single_collective_bill_missing():
    db = SessionLocal()
    try:
        suffix = uuid4().hex[:8]
        ch = ensure_country(db, "CH")
        hc = HireCompany(name=f"HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(name=f"Org {suffix}", country_id=ch, hire_company_id=hc.id, currency="CHF")
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        ev = Event(name="E", status="active", start=now, end=now, organisation_id=org.id)
        db.add(ev)
        db.commit()
        assert build_single_collective_bill(db, ev, "missing") is None
    finally:
        db.close()


def _pdf_route_fixture() -> tuple[str, int, str]:
    suffix = uuid4().hex[:8]
    db = SessionLocal()
    try:
        ch = ensure_country(db, "CH")
        hc = HireCompany(name=f"PDF HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"PDF Route Org {suffix}",
            country_id=ch,
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        ev = Event(
            name="Route Fest",
            status="prod",
            start=now,
            end=now,
            organisation_id=org.id,
            payment_mode="pay_now",
            payment_types=["cash"],
        )
        db.add(ev)
        db.flush()
        db.add(Appliance(hire_company_id=hc.id, type="pi", name="Pi"))
        db.flush()
        bill_uuid = f"cb-route-{suffix}"
        payload = {
            "collective_bill_uuid": bill_uuid,
            "collective_bill_name": "VIP",
            "payment_status": "open",
            "lines": [{"article_id": 1, "qty": 1, "unit_cents": 800, "additions": []}],
        }
        upsert_collective_bill_from_payload(db, event_id=ev.id, appliance_id=db.query(Appliance).first().id, payload=payload)
        db.add(
            EdgeSubmittedOrder(
                client_order_id=f"order-{suffix}",
                appliance_id=db.query(Appliance).first().id,
                organisation_id=org.id,
                event_id=ev.id,
                payload=payload,
            )
        )
        db.add(
            User(
                email=f"pdf-{suffix}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return f"pdf-{suffix}@test.local", ev.id, bill_uuid
    finally:
        db.close()


def _token(email: str) -> str:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_collective_bill_pdf_route():
    email, event_id, bill_uuid = _pdf_route_fixture()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    r = client.get(f"/events/{event_id}/collective-bills/{bill_uuid}/pdf", headers=headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")
    assert "Sammelrechnung" in r.headers.get("content-disposition", "")


def test_collective_bill_pdf_route_not_found():
    email, event_id, _ = _pdf_route_fixture()
    headers = {"Authorization": f"Bearer {_token(email)}"}
    r = client.get(f"/events/{event_id}/collective-bills/does-not-exist/pdf", headers=headers)
    assert r.status_code == 404
