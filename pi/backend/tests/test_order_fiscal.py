"""Per-event order numbers and distinct order counts."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, apply_schema_patches
from app.main import app
from app.models import LocalOrder, SyncedBundle


@pytest.fixture
def client():
    import app.database as database

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.engine = engine
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    Session = database.SessionLocal
    db = Session()
    bundle = {
        "organisation_id": 1,
        "events": [
            {
                "id": 1,
                "name": "Test",
                "currency": "CHF",
                "payment_mode": "pay_later",
                "payment_types": ["cash"],
                "articles": {
                    "10": {"id": 10, "name": "Bier", "price": 5.0, "additions": []},
                },
                "configuration": {
                    "stations": [],
                    "waiters": [{"uuid": "w-1", "name": "Anna"}],
                },
            }
        ],
    }
    db.add(SyncedBundle(id=1, json_body=json.dumps(bundle)))
    db.commit()
    db.close()

    from app.routers import edge_api

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[edge_api.get_db] = override_get_db
    with TestClient(app) as c:
        yield c, Session
    app.dependency_overrides.clear()


def _ferdig(client, table: int = 5, qty: int = 1):
    cid = f"pwa-{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "table_number": table,
            "waiter_uuid": "w-1",
            "lines": [{"article_id": 10, "qty": qty, "note": "", "additions": []}],
        },
    )
    assert r.status_code == 200, r.text
    return r.json(), cid


def test_ferdig_assigns_sequential_order_numbers(client):
    c, _ = client
    r1, _ = _ferdig(c, table=1)
    r2, _ = _ferdig(c, table=2)
    assert r1["order_number"] == 1
    assert r2["order_number"] == 2


def test_ferdig_payload_snapshots(client):
    c, Session = client
    body, cid = _ferdig(c)
    assert body["order_number"] == 1

    db = Session()
    row = db.query(LocalOrder).filter(LocalOrder.client_order_id == cid).first()
    payload = json.loads(row.payload_json)
    db.close()

    assert payload["order_number"] == 1
    assert payload.get("ordered_at")
    assert payload.get("waiter_name") == "Anna"
    line = payload["lines"][0]
    assert line["unit_cents"] == 500
    assert line["article_name"] == "Bier"


def test_table_order_count_uses_distinct_order_numbers(client):
    c, _ = client
    _ferdig(c, table=7)
    _ferdig(c, table=7)

    r = c.get("/v1/tables/open", params={"event_id": 1})
    assert r.status_code == 200
    table = next(t for t in r.json()["tables"] if t["table_number"] == 7)
    assert table["order_count"] == 2


def test_non_ferdig_submission_has_no_order_number(client):
    c, _ = client
    cid = f"ord-{uuid.uuid4().hex[:8]}"
    r = c.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "table_number": 3,
            "lines": [{"article_id": 10, "qty": 1, "note": "", "additions": []}],
        },
    )
    assert r.status_code == 200
    assert r.json().get("order_number") is None


def test_settle_partial_uses_line_snapshot_prices(client):
    """Payment amount must match line_groups unit_cents, not current bundle article price."""
    c, Session = client
    db = Session()
    db.add(
        LocalOrder(
            client_order_id="snap-order-1",
            event_id=1,
            table_number=9,
            payment_status="open",
            payload_json=json.dumps(
                {
                    "event_id": 1,
                    "table_number": 9,
                    "payment_status": "open",
                    "lines": [
                        {
                            "article_id": 10,
                            "qty": 1,
                            "note": "",
                            "additions": [],
                            "unit_cents": 3950,
                            "article_name": "Bier",
                        }
                    ],
                }
            ),
        )
    )
    db.commit()
    db.close()

    summary = c.get("/v1/tables/9", params={"event_id": 1})
    assert summary.status_code == 200
    group = summary.json()["line_groups"][0]
    assert group["unit_cents"] == 3950

    r = c.post(
        "/v1/tables/9/settle-partial",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": 3950}],
            "selections": [
                {"article_id": 10, "qty": 1, "note": "", "additions": []},
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["paid_cents"] == 3950

