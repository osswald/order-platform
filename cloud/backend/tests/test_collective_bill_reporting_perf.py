"""SQL-scoped collective-bill membership, backfill, close, and single-bill load."""

from datetime import UTC, datetime

import pytest
from app.database import Base
from app.event_collective_bills import (
    backfill_edge_submitted_order_collective_bill_uuids,
    build_event_collective_bills_list,
    build_single_collective_bill,
    collective_bill_uuid_from_payload,
    load_collective_orders_for_event,
    load_orders_for_collective_bill,
    upsert_collective_bill_from_payload,
)
from app.models import (
    Appliance,
    EdgeSubmittedOrder,
    Event,
    EventCollectiveBill,
    HireCompany,
    Organisation,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.helpers import ensure_country


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    ch_country_id = ensure_country(db, "CH", country_id=1)
    db.add(HireCompany(id=1, name="HC"))
    db.add(Organisation(id=1, hire_company_id=1, name="Org", country_id=ch_country_id, currency="CHF"))
    now = datetime.now(UTC)
    ev = Event(
        id=1,
        name="Fest",
        status="active",
        start=now,
        end=now,
        organisation_id=1,
        payment_mode="pay_later",
    )
    db.add(ev)
    db.add(Appliance(id=1, hire_company_id=1, type="pi", name="Pi"))
    db.commit()
    yield db, ev
    db.close()


def _order_payload(*, bill_uuid: str | None, status: str = "open", cents: int = 500) -> dict:
    payload: dict = {
        "payment_status": status,
        "lines": [{"article_id": 1, "qty": 1, "unit_cents": cents, "note": "", "additions": []}],
    }
    if bill_uuid is not None:
        payload["collective_bill_uuid"] = bill_uuid
        payload["collective_bill_name"] = "Personal"
    if status == "paid":
        payload["payments"] = [{"type": "cash", "amount_cents": cents}]
    return payload


def test_collective_bill_uuid_from_payload_normalizes_empty():
    assert collective_bill_uuid_from_payload(None) is None
    assert collective_bill_uuid_from_payload({}) is None
    assert collective_bill_uuid_from_payload({"collective_bill_uuid": ""}) is None
    assert collective_bill_uuid_from_payload({"collective_bill_uuid": "  "}) is None
    assert collective_bill_uuid_from_payload({"collective_bill_uuid": " cb-1 "}) == "cb-1"


def test_backfill_sets_column_from_payload(db_session):
    db, event = db_session
    payload = _order_payload(bill_uuid="cb-backfill")
    db.add(
        EdgeSubmittedOrder(
            client_order_id="legacy-1",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            collective_bill_uuid=None,
            payload=payload,
        )
    )
    db.add(
        EdgeSubmittedOrder(
            client_order_id="empty-uuid",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            collective_bill_uuid=None,
            payload={**payload, "collective_bill_uuid": ""},
        )
    )
    db.commit()

    updated = backfill_edge_submitted_order_collective_bill_uuids(db)
    db.commit()
    assert updated == 1

    row = db.query(EdgeSubmittedOrder).filter_by(client_order_id="legacy-1").one()
    assert row.collective_bill_uuid == "cb-backfill"
    empty = db.query(EdgeSubmittedOrder).filter_by(client_order_id="empty-uuid").one()
    assert empty.collective_bill_uuid is None

    loaded = load_collective_orders_for_event(db, event.id)
    assert [o.client_order_id for o in loaded] == ["legacy-1"]


def test_list_skips_non_collective_orders(db_session):
    db, event = db_session
    bill_payload = _order_payload(bill_uuid="cb-only")
    upsert_collective_bill_from_payload(db, event_id=event.id, appliance_id=1, payload=bill_payload)
    db.add(
        EdgeSubmittedOrder(
            client_order_id="bill-order",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            collective_bill_uuid="cb-only",
            payload=bill_payload,
        )
    )
    for i in range(50):
        plain = _order_payload(bill_uuid=None)
        db.add(
            EdgeSubmittedOrder(
                client_order_id=f"plain-{i}",
                appliance_id=1,
                organisation_id=1,
                event_id=event.id,
                collective_bill_uuid=None,
                payload=plain,
            )
        )
    db.commit()

    membership = load_collective_orders_for_event(db, event.id)
    assert len(membership) == 1
    assert membership[0].client_order_id == "bill-order"

    result = build_event_collective_bills_list(db, event)
    assert len(result["collective_bills"]) == 1
    assert result["collective_bills"][0]["uuid"] == "cb-only"
    assert result["collective_bills"][0]["order_count"] == 1


def test_close_ignores_unrelated_open_orders(db_session):
    db, event = db_session
    paid = _order_payload(bill_uuid="cb-close", status="paid")
    upsert_collective_bill_from_payload(db, event_id=event.id, appliance_id=1, payload=paid)
    db.add(
        EdgeSubmittedOrder(
            client_order_id="paid-bill",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            collective_bill_uuid="cb-close",
            payload=paid,
        )
    )
    open_plain = _order_payload(bill_uuid=None, status="open")
    db.add(
        EdgeSubmittedOrder(
            client_order_id="open-other",
            appliance_id=1,
            organisation_id=1,
            event_id=event.id,
            collective_bill_uuid=None,
            payload=open_plain,
        )
    )
    db.commit()

    # Re-run close detection after order row exists.
    upsert_collective_bill_from_payload(db, event_id=event.id, appliance_id=1, payload=paid)
    db.commit()

    header = db.query(EventCollectiveBill).filter_by(uuid="cb-close").one()
    assert header.closed_at is not None


def test_single_bill_does_not_require_other_bills(db_session):
    db, event = db_session
    for uuid, cid in (("cb-a", "a1"), ("cb-b", "b1")):
        payload = _order_payload(bill_uuid=uuid)
        upsert_collective_bill_from_payload(db, event_id=event.id, appliance_id=1, payload=payload)
        db.add(
            EdgeSubmittedOrder(
                client_order_id=cid,
                appliance_id=1,
                organisation_id=1,
                event_id=event.id,
                collective_bill_uuid=uuid,
                payload=payload,
            )
        )
    db.commit()

    only_b = load_orders_for_collective_bill(db, event.id, "cb-b")
    assert len(only_b) == 1
    assert only_b[0].client_order_id == "b1"

    single = build_single_collective_bill(db, event, "cb-b")
    assert single is not None
    assert single["uuid"] == "cb-b"
    assert single["order_count"] == 1
    assert single.get("_currency") == "CHF"

    missing = build_single_collective_bill(db, event, "cb-missing")
    assert missing is None


def test_ingest_denormalize_skips_operational_entity_types():
    """Cash/kitchen chunk payloads must not gain membership even if a UUID key is present."""
    payload = {"collective_bill_uuid": "cb-should-ignore", "entity_type": "cash_session"}
    entity_type = "cash_session"
    bill_uuid = (
        None
        if entity_type in {"cash_session", "cash_drawer", "kitchen_tickets"}
        else collective_bill_uuid_from_payload(payload)
    )
    assert bill_uuid is None
    assert collective_bill_uuid_from_payload({"collective_bill_uuid": "cb-order"}) == "cb-order"
