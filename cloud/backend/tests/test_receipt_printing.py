"""Receipt printing configuration and copy behaviour."""

import base64
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Event, HireCompany, Organisation
from app.receipt_printing_config import (
    copy_receipt_printing_from_hire_company,
    copy_receipt_printing_from_organisation,
    default_event_printing_config,
    normalize_event_config,
    printing_bundle_dict,
    store_receipt_logo,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_copy_hire_company_to_organisation(db):
    hire = HireCompany(name="Vendor")
    db.add(hire)
    db.flush()
    hire.receipt_printing_config = {
        "station_receipt": {"show_price": True, "bottom_line": "Kitchen"},
        "customer_receipt": {"show_price": False},
    }
    store_receipt_logo(hire, "image/png", b"\x89PNG\r\n\x1a\n")

    org = Organisation(name="Org", country="CH", hire_company_id=hire.id)
    db.add(org)
    db.flush()
    copy_receipt_printing_from_hire_company(hire, org)

    assert org.receipt_printing_config["station_receipt"]["show_price"] is True
    assert org.receipt_logo_mime == "image/png"
    assert org.receipt_logo_data


def test_copy_organisation_to_event_includes_label(db):
    org = Organisation(name="Org", country="CH", hire_company_id=1)
    db.add(HireCompany(id=1, name="V"))
    db.add(org)
    db.flush()
    org.receipt_printing_config = default_event_printing_config()
    org.receipt_printing_config["label_event_title"] = "ignored on org"

    start = datetime(2026, 6, 1, 10, tzinfo=timezone.utc)
    end = datetime(2026, 6, 1, 22, tzinfo=timezone.utc)
    event = Event(
        name="Fest",
        status="config",
        start=start,
        end=end,
        currency="CHF",
        organisation_id=org.id,
    )
    db.add(event)
    db.flush()
    copy_receipt_printing_from_organisation(org, event)

    assert "label_event_title" in event.receipt_printing_config
    assert event.receipt_printing_config["label_event_title"] == ""


def test_printing_bundle_dict_includes_logo_base64(db):
    start = datetime(2026, 6, 1, 10, tzinfo=timezone.utc)
    end = datetime(2026, 6, 1, 22, tzinfo=timezone.utc)
    event = Event(
        name="Fest",
        status="config",
        start=start,
        end=end,
        currency="CHF",
        organisation_id=1,
    )
    store_receipt_logo(event, "image/png", b"fakepng")
    event.receipt_printing_config = normalize_event_config(
        {"label_event_title": "My Fest", "station_receipt": {"show_price": True}}
    )
    bundle = printing_bundle_dict(event)
    assert bundle["label_event_title"] == "My Fest"
    assert bundle["station_receipt"]["show_price"] is True
    assert bundle["payment_receipt"]["size_order_lines"] == "normal"
    assert bundle["logo_base64"] == base64.b64encode(b"fakepng").decode("ascii")
