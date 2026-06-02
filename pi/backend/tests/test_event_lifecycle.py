"""Pi event lifecycle: purge local data on status changes."""

import json
import uuid

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import run_migrations
from app.event_lifecycle import purge_event_local_data, reconcile_bundle_lifecycle
from app.models import (
    CollectiveBill,
    EventOrderCounter,
    LocalOrder,
    OutboxEntry,
    PrintJob,
)
from app.models_operational import OrderSession


def _submission_count(db) -> int:
    return int(db.execute(select(func.count()).select_from(LocalOrder)).scalar_one())


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app import database

    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine)
    run_migrations()
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_event_data(session, event_id: int = 1):
    session.add(OrderSession(event_id=event_id, table_number=1, order_source="waiter", status="OPEN"))
    session.flush()
    session_id = session.query(OrderSession).first().id
    order = LocalOrder(
        session_id=session_id,
        client_order_id=f"o-{event_id}",
        event_id=event_id,
        table_number=1,
        payment_status="open",
        payload_json="{}",
    )
    session.add(order)
    session.flush()
    session.add(
        PrintJob(
            local_order_id=order.id,
            printer_host="10.0.0.1",
            escpos_payload="e30=",
            status="queued",
        )
    )
    session.add(
        OutboxEntry(
            chunk_id=str(uuid.uuid4()),
            entity_type="submission",
            entity_ids_json="[]",
            event_id=event_id,
            payload_json=json.dumps({"client_order_id": f"o-{event_id}"}),
            status="pending",
        )
    )
    session.add(CollectiveBill(uuid=f"cb-{event_id}", event_id=event_id, name="Team"))
    session.add(EventOrderCounter(event_id=event_id, next_number=5))
    session.commit()


def test_purge_event_local_data(db):
    _seed_event_data(db, 1)
    purge_event_local_data(db, 1)
    db.commit()
    assert _submission_count(db) == 0
    assert db.query(OutboxEntry).count() == 0
    assert db.query(PrintJob).count() == 0
    assert db.query(CollectiveBill).count() == 0
    assert db.query(EventOrderCounter).count() == 0


def test_reconcile_test_to_prod_purges(db):
    _seed_event_data(db, 1)
    old_bundle = {"events": [{"id": 1, "status": "test"}]}
    new_bundle = {"events": [{"id": 1, "status": "prod"}]}
    purged = reconcile_bundle_lifecycle(db, old_bundle, new_bundle)
    assert purged == [1]
    assert _submission_count(db) == 0


def test_reconcile_prod_to_prod_no_purge(db):
    _seed_event_data(db, 1)
    bundle = {"events": [{"id": 1, "status": "prod"}]}
    purged = reconcile_bundle_lifecycle(db, bundle, bundle)
    assert purged == []
    assert _submission_count(db) == 1


def test_reconcile_event_removed_from_bundle_purges(db):
    _seed_event_data(db, 1)
    old_bundle = {"events": [{"id": 1, "status": "test"}]}
    new_bundle = {"events": []}
    purged = reconcile_bundle_lifecycle(db, old_bundle, new_bundle)
    assert purged == [1]
    assert _submission_count(db) == 0


def test_pull_bundle_order_pull_before_push():
    import inspect

    from app import sync_service

    src = inspect.getsource(sync_service.run_sync_cycle)
    pull_idx = src.index("pull_result = await pull_bundle")
    push_idx = src.index("push_result = await push_outbox")
    assert pull_idx < push_idx
