"""Table transfer and collective bill assign/settle."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, apply_schema_patches
from app.main import app
from app.models import CollectiveBill, LocalOrder, SyncedBundle


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
                "configuration": {"stations": []},
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
        yield c
    app.dependency_overrides.clear()


def _add_table_order(client, table: int, qty: int = 2):
    cid = f"ord-{table}-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/v1/orders",
        json={
            "client_order_id": cid,
            "event_id": 1,
            "table_number": table,
            "lines": [{"article_id": 10, "qty": qty, "note": "", "additions": []}],
        },
    )
    assert r.status_code == 200, r.text
    return cid


def test_transfer_lines_between_tables(client):
    _add_table_order(client, 5, qty=3)
    r = client.post(
        "/v1/tables/5/transfer-lines",
        json={
            "event_id": 1,
            "target_table_number": 8,
            "selections": [{"article_id": 10, "note": "", "qty": 1, "additions": []}],
        },
    )
    assert r.status_code == 200
    src = client.get("/v1/tables/5?event_id=1").json()
    dst = client.get("/v1/tables/8?event_id=1").json()
    assert src["total_cents"] == 1000  # 2 beers left
    assert dst["total_cents"] == 500


def test_assign_to_collective_twice(client):
    _add_table_order(client, 3, qty=2)
    r1 = client.post(
        "/v1/tables/3/assign-collective",
        json={
            "event_id": 1,
            "new_name": "Personal",
            "selections": [{"article_id": 10, "note": "", "qty": 1, "additions": []}],
        },
    )
    assert r1.status_code == 200
    bill_id = r1.json()["collective_bill_id"]
    _add_table_order(client, 7, qty=1)
    r2 = client.post(
        "/v1/tables/7/assign-collective",
        json={
            "event_id": 1,
            "collective_bill_id": bill_id,
            "selections": [{"article_id": 10, "note": "", "qty": 1, "additions": []}],
        },
    )
    assert r2.status_code == 200
    summary = client.get(f"/v1/collective-bills/{bill_id}?event_id=1").json()
    assert summary["total_cents"] == 1000
    assert summary["name"] == "Personal"


def test_schema_patch_creates_collective_bills_table():
    import app.database as database
    from app.database import apply_schema_patches

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                "CREATE TABLE local_orders (id INTEGER PRIMARY KEY, client_order_id VARCHAR(64))"
            )
        )
    database.engine = engine
    apply_schema_patches()
    inspector = __import__("sqlalchemy").inspect(engine)
    assert "collective_bills" in inspector.get_table_names()


def test_empty_collective_bill_in_open_list(client):
    created = client.post(
        "/v1/collective-bills",
        json={"event_id": 1, "name": "Leer"},
    )
    assert created.status_code == 200, created.text
    bill_id = created.json()["id"]
    open_list = client.get("/v1/collective-bills/open?event_id=1").json()
    ids = [b["id"] for b in open_list["collective_bills"]]
    assert bill_id in ids
    empty = next(b for b in open_list["collective_bills"] if b["id"] == bill_id)
    assert empty["total_cents"] == 0
    assert empty["order_count"] == 0


def test_settled_collective_bill_not_in_open_list(client):
    _add_table_order(client, 2, qty=1)
    assign = client.post(
        "/v1/tables/2/assign-collective",
        json={
            "event_id": 1,
            "new_name": "Done",
            "selections": [{"article_id": 10, "note": "", "qty": 1, "additions": []}],
        },
    )
    assert assign.status_code == 200
    bill_id = assign.json()["collective_bill_id"]
    summary = client.get(f"/v1/collective-bills/{bill_id}?event_id=1").json()
    total = summary["total_cents"]
    settle = client.post(
        f"/v1/collective-bills/{bill_id}/settle",
        json={
            "event_id": 1,
            "payments": [{"type": "cash", "amount_cents": total}],
        },
    )
    assert settle.status_code == 200, settle.text
    open_list = client.get("/v1/collective-bills/open?event_id=1").json()
    assert bill_id not in [b["id"] for b in open_list["collective_bills"]]


def test_open_tables_exclude_collective(client):
    _add_table_order(client, 1, qty=1)
    client.post(
        "/v1/tables/1/assign-collective",
        json={
            "event_id": 1,
            "new_name": "Helfer",
            "selections": [{"article_id": 10, "note": "", "qty": 1, "additions": []}],
        },
    )
    open_tables = client.get("/v1/collective-bills/open?event_id=1").json()
    assert len(open_tables["collective_bills"]) == 1
    tables = client.get("/v1/tables/open?event_id=1").json()
    assert tables["tables"] == []
