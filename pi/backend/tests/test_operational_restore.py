"""Operational restore from cloud snapshot."""

import json

import pytest
from app.models import KitchenTicket, KitchenTicketLine, LocalOrder
from app.operational_restore import needs_operational_restore, restore_operational_snapshot
from tests.fixtures_bundles import bundle_copy, kitchen_monitor_bundle


@pytest.fixture
def bundle():
    return bundle_copy(kitchen_monitor_bundle())


def test_restore_open_table_from_snapshot(isolated_engine, db_session, bundle):
    db = db_session
    from app.models import SyncedBundle

    db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    db.commit()

    snapshot = {
        "organisation_id": 1,
        "events": [
            {
                "event_id": 1,
                "open_orders": [
                    {
                        "client_order_id": "restored-order-1",
                        "payload": {
                            "client_order_id": "restored-order-1",
                            "event_id": 1,
                            "table_number": 12,
                            "payment_status": "open",
                            "waiter_uuid": "w-1",
                            "lines": [
                                {
                                    "article_id": 10,
                                    "qty": 1,
                                    "station_uuid": "st-kitchen",
                                    "note": "",
                                    "additions": [],
                                }
                            ],
                        },
                    }
                ],
                "collective_bills": [],
                "open_cash_sessions": [],
                "kitchen_tickets": [
                    {
                        "client_order_id": "restored-order-1",
                        "tickets": [
                            {
                                "station_uuid": "st-kitchen",
                                "printer_appliance_id": 101,
                                "status": "partial",
                                "lines": [
                                    {
                                        "line_index": 0,
                                        "line_payload": {"article_id": 10, "qty": 1},
                                        "qty_total": 1,
                                        "qty_printed": 1,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    assert needs_operational_restore(db, snapshot) is True
    summary = restore_operational_snapshot(db, snapshot, bundle)
    assert summary["restored_orders"] == 1
    assert summary["restored_kitchen_tickets"] == 1

    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == "restored-order-1").one()
    assert order.table_number == 12
    ticket = db.query(KitchenTicket).filter(KitchenTicket.local_order_id == order.id).one()
    assert ticket.status == "partial"
    line = db.query(KitchenTicketLine).filter(KitchenTicketLine.ticket_id == ticket.id).one()
    assert line.qty_printed == 1


def test_needs_restore_false_when_matching(isolated_engine, db_session, bundle):
    db = db_session
    from app.domain.sessions import ensure_order_session
    from app.models import SyncedBundle

    db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    payload = {
        "client_order_id": "same-order",
        "table_number": 3,
        "payment_status": "open",
        "lines": [{"article_id": 10, "qty": 1}],
    }
    session_id = ensure_order_session(db, event_id=1, table_number=3, waiter_uuid="w-1", order_source="waiter")
    db.add(
        LocalOrder(
            session_id=session_id,
            client_order_id="same-order",
            event_id=1,
            table_number=3,
            payment_status="open",
            payload_json=json.dumps(payload),
        )
    )
    db.commit()

    snapshot = {
        "events": [
            {
                "event_id": 1,
                "open_orders": [{"client_order_id": "same-order", "payload": payload}],
                "collective_bills": [],
                "open_cash_sessions": [],
                "kitchen_tickets": [],
            }
        ]
    }
    assert needs_operational_restore(db, snapshot) is False
