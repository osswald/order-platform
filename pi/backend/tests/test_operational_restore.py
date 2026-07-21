"""Operational restore from cloud snapshot."""

import json

import pytest
from app.domain.sessions import ensure_order_session
from app.models import KitchenTicket, KitchenTicketLine, LocalOrder, OutboxEntry, SyncedBundle
from app.operational_restore import needs_operational_restore, restore_operational_snapshot
from tests.fixtures_bundles import bundle_copy, kitchen_monitor_bundle


@pytest.fixture
def bundle():
    return bundle_copy(kitchen_monitor_bundle())


def _seed_bundle(db, bundle):
    db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    db.commit()


def _open_line(*, article_id: int = 10, qty: int = 1) -> dict:
    return {
        "article_id": article_id,
        "qty": qty,
        "station_uuid": "st-kitchen",
        "note": "",
        "additions": [],
    }


def _cloud_open_order(
    cid: str,
    *,
    table_number: int = 12,
    lines: list[dict] | None = None,
) -> dict:
    return {
        "client_order_id": cid,
        "payload": {
            "client_order_id": cid,
            "event_id": 1,
            "table_number": table_number,
            "payment_status": "open",
            "waiter_uuid": "w-1",
            "lines": lines if lines is not None else [_open_line()],
        },
    }


def _cloud_kitchen_partial(cid: str) -> dict:
    return {
        "client_order_id": cid,
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


def _event_snapshot(
    *,
    open_orders: list[dict],
    kitchen_tickets: list[dict] | None = None,
) -> dict:
    return {
        "organisation_id": 1,
        "events": [
            {
                "event_id": 1,
                "open_orders": open_orders,
                "collective_bills": [],
                "open_cash_sessions": [],
                "kitchen_tickets": kitchen_tickets if kitchen_tickets is not None else [],
            }
        ],
    }


def _add_local_order(
    db,
    *,
    cid: str,
    payment_status: str = "open",
    table_number: int = 12,
    lines: list[dict] | None = None,
) -> LocalOrder:
    lines = lines if lines is not None else [_open_line()]
    payload = {
        "client_order_id": cid,
        "event_id": 1,
        "table_number": table_number,
        "payment_status": payment_status,
        "waiter_uuid": "w-1",
        "lines": lines,
    }
    session_id = ensure_order_session(
        db, event_id=1, table_number=table_number, waiter_uuid="w-1", order_source="waiter"
    )
    order = LocalOrder(
        session_id=session_id,
        client_order_id=cid,
        event_id=1,
        table_number=table_number,
        payment_status=payment_status,
        payload_json=json.dumps(payload),
        print_status="done",
    )
    db.add(order)
    db.flush()
    return order


def _add_done_kitchen_ticket(db, order: LocalOrder) -> KitchenTicket:
    ticket = KitchenTicket(
        local_order_id=order.id,
        order_submission_id=order.id,
        event_id=order.event_id,
        station_uuid="st-kitchen",
        printer_appliance_id=101,
        status="done",
    )
    db.add(ticket)
    db.flush()
    db.add(
        KitchenTicketLine(
            ticket_id=ticket.id,
            line_index=0,
            line_payload_json=json.dumps({"article_id": 10, "qty": 1}),
            qty_total=1,
            qty_printed=1,
        )
    )
    db.flush()
    return ticket


def test_restore_open_table_from_snapshot(isolated_engine, db_session, bundle):
    db = db_session
    _seed_bundle(db, bundle)

    snapshot = _event_snapshot(
        open_orders=[_cloud_open_order("restored-order-1")],
        kitchen_tickets=[_cloud_kitchen_partial("restored-order-1")],
    )

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
    _seed_bundle(db, bundle)
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


def test_restore_keeps_local_all_done_kitchen_when_cloud_kitchen_empty(
    isolated_engine, db_session, bundle
):
    db = db_session
    _seed_bundle(db, bundle)
    order = _add_local_order(db, cid="done-kitchen-1")
    ticket = _add_done_kitchen_ticket(db, order)
    ticket_id = ticket.id
    db.commit()

    snapshot = _event_snapshot(open_orders=[_cloud_open_order("done-kitchen-1")], kitchen_tickets=[])
    summary = restore_operational_snapshot(db, snapshot, bundle)

    assert summary["restored_kitchen_tickets"] == 0
    kept = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).one()
    assert kept.status == "done"
    assert db.query(KitchenTicket).filter(KitchenTicket.local_order_id == order.id).count() == 1
    assert (
        db.query(KitchenTicket)
        .filter(KitchenTicket.local_order_id == order.id, KitchenTicket.status != "done")
        .count()
        == 0
    )


def test_restore_keeps_local_all_done_kitchen_when_cloud_has_stale_open(
    isolated_engine, db_session, bundle
):
    db = db_session
    _seed_bundle(db, bundle)
    order = _add_local_order(db, cid="done-kitchen-2")
    ticket = _add_done_kitchen_ticket(db, order)
    ticket_id = ticket.id
    db.commit()

    snapshot = _event_snapshot(
        open_orders=[_cloud_open_order("done-kitchen-2")],
        kitchen_tickets=[_cloud_kitchen_partial("done-kitchen-2")],
    )
    summary = restore_operational_snapshot(db, snapshot, bundle)

    assert summary["restored_kitchen_tickets"] == 0
    kept = db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).one()
    assert kept.status == "done"
    assert db.query(KitchenTicket).filter(KitchenTicket.local_order_id == order.id).one().status == "done"


def test_restore_does_not_regen_kitchen_when_cloud_kitchen_empty(
    isolated_engine, db_session, bundle
):
    db = db_session
    _seed_bundle(db, bundle)

    snapshot = _event_snapshot(open_orders=[_cloud_open_order("no-kitchen-1")], kitchen_tickets=[])
    summary = restore_operational_snapshot(db, snapshot, bundle)

    assert summary["restored_orders"] == 1
    assert summary["restored_kitchen_tickets"] == 0
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == "no-kitchen-1").one()
    assert order.payment_status == "open"
    assert db.query(KitchenTicket).filter(KitchenTicket.local_order_id == order.id).count() == 0


def test_restore_applies_cloud_kitchen_on_empty_local(isolated_engine, db_session, bundle):
    """Takeover path: empty local + cloud kitchen tickets still apply."""
    db = db_session
    _seed_bundle(db, bundle)

    snapshot = _event_snapshot(
        open_orders=[_cloud_open_order("takeover-1")],
        kitchen_tickets=[_cloud_kitchen_partial("takeover-1")],
    )
    summary = restore_operational_snapshot(db, snapshot, bundle)

    assert summary["restored_orders"] == 1
    assert summary["restored_kitchen_tickets"] == 1
    order = db.query(LocalOrder).filter(LocalOrder.client_order_id == "takeover-1").one()
    ticket = db.query(KitchenTicket).filter(KitchenTicket.local_order_id == order.id).one()
    assert ticket.status == "partial"


def test_restore_does_not_reopen_local_paid_order(isolated_engine, db_session, bundle):
    db = db_session
    _seed_bundle(db, bundle)
    order = _add_local_order(db, cid="paid-1", payment_status="paid")
    ticket = _add_done_kitchen_ticket(db, order)
    ticket_id = ticket.id
    paid_payload = json.loads(order.payload_json)
    db.commit()

    cloud = _cloud_open_order("paid-1")
    cloud["payload"]["lines"] = [_open_line(qty=3)]
    snapshot = _event_snapshot(
        open_orders=[cloud],
        kitchen_tickets=[_cloud_kitchen_partial("paid-1")],
    )
    summary = restore_operational_snapshot(db, snapshot, bundle)

    assert summary["restored_orders"] == 0
    assert summary["restored_kitchen_tickets"] == 0
    refreshed = db.query(LocalOrder).filter(LocalOrder.client_order_id == "paid-1").one()
    assert refreshed.payment_status == "paid"
    assert json.loads(refreshed.payload_json) == paid_payload
    assert db.query(KitchenTicket).filter(KitchenTicket.id == ticket_id).one().status == "done"


def test_restore_skips_local_open_with_pending_outbox(isolated_engine, db_session, bundle):
    db = db_session
    _seed_bundle(db, bundle)
    local_lines = [_open_line(qty=1)]
    order = _add_local_order(db, cid="pending-1", lines=local_lines)
    local_payload = json.loads(order.payload_json)
    db.add(
        OutboxEntry(
            chunk_id="chunk-pending-1",
            entity_type="submission",
            entity_ids_json=json.dumps(["pending-1"]),
            event_id=1,
            payload_json=json.dumps(local_payload),
            payload_version=1,
            status="pending",
        )
    )
    db.commit()

    cloud = _cloud_open_order("pending-1", lines=[_open_line(qty=5)])
    snapshot = _event_snapshot(open_orders=[cloud], kitchen_tickets=[])
    summary = restore_operational_snapshot(db, snapshot, bundle)

    assert summary["restored_orders"] == 0
    refreshed = db.query(LocalOrder).filter(LocalOrder.client_order_id == "pending-1").one()
    assert json.loads(refreshed.payload_json)["lines"] == local_lines
    assert refreshed.payment_status == "open"


def test_restore_keeps_local_fewer_lines_than_cloud(isolated_engine, db_session, bundle):
    db = db_session
    _seed_bundle(db, bundle)
    local_lines = [_open_line(qty=1)]
    order = _add_local_order(db, cid="partial-1", lines=local_lines)
    local_payload = json.loads(order.payload_json)
    db.commit()

    cloud = _cloud_open_order("partial-1", lines=[_open_line(qty=4)])
    snapshot = _event_snapshot(open_orders=[cloud], kitchen_tickets=[])
    summary = restore_operational_snapshot(db, snapshot, bundle)

    assert summary["restored_orders"] == 0
    refreshed = db.query(LocalOrder).filter(LocalOrder.client_order_id == "partial-1").one()
    assert json.loads(refreshed.payload_json) == local_payload
    assert json.loads(refreshed.payload_json)["lines"] == local_lines
