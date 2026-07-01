"""Operational chunk sync deducts cloud stock like legacy edge order POST."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    ApplianceLending,
    Article,
    ArticleCategory,
    Event,
    EventArticleStock,
    EventStation,
    HireCompany,
    Organisation,
)
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _edge_stock_fixture(*, in_stock: int = 20) -> tuple[dict[str, str], int, int]:
    suffix = uuid4().hex
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"Stock HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"Stock Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        cat = ArticleCategory(name="Food", organisation_id=org.id)
        db.add(cat)
        db.flush()
        art = Article(name="Cervelat", label="C", price=5.0, article_category_id=cat.id)
        db.add(art)
        db.flush()
        now = datetime.now(UTC)
        ev = Event(
            name="Live",
            status="prod",
            start=now - timedelta(hours=1),
            end=now + timedelta(days=1),
            organisation_id=org.id,
            payment_mode="pay_later",
            payment_types=["cash"],
        )
        db.add(ev)
        db.flush()
        st = EventStation(event_id=ev.id, uuid=f"st-{suffix}", name="Grill", sort_order=0)
        st.articles = [art]
        db.add(st)
        db.add(
            EventArticleStock(
                event_id=ev.id,
                article_id=art.id,
                monitor_stock=True,
                in_stock=in_stock,
                baseline_in_stock=in_stock,
            )
        )
        appliance = Appliance(hire_company_id=hc.id, type="server", name="Pi")
        db.add(appliance)
        db.flush()
        today = now.date()
        db.add(
            ApplianceLending(
                appliance_id=appliance.id,
                organisation_id=org.id,
                start_date=today,
                end_date=today,
                returned_at=None,
            )
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
            {"X-Edge-Client-Id": cred.edge_client_id, "X-Edge-Secret": secret},
            ev.id,
            art.id,
        )
    finally:
        db.close()


def test_operational_chunk_deducts_event_stock():
    headers, event_id, article_id = _edge_stock_fixture(in_stock=20)
    chunk_id = f"chunk-{uuid4().hex}"
    res = client.post(
        "/edge/v1/sync/operational/chunk",
        headers=headers,
        json={
            "chunk_id": chunk_id,
            "event_id": event_id,
            "entity_type": "submission",
            "payload": {
                "client_order_id": f"order-{uuid4().hex}",
                "payment_status": "open",
                "lines": [{"article_id": article_id, "qty": 3, "unit_cents": 500}],
            },
        },
    )
    assert res.status_code == 200, res.text

    db = SessionLocal()
    try:
        row = (
            db.query(EventArticleStock)
            .filter(EventArticleStock.event_id == event_id, EventArticleStock.article_id == article_id)
            .one()
        )
        assert row.in_stock == 17
        assert row.baseline_in_stock == 20
    finally:
        db.close()


def test_operational_chunk_duplicate_does_not_double_deduct():
    headers, event_id, article_id = _edge_stock_fixture(in_stock=20)
    chunk_id = f"chunk-{uuid4().hex}"
    payload = {
        "chunk_id": chunk_id,
        "event_id": event_id,
        "entity_type": "submission",
        "payload": {
            "client_order_id": f"order-{uuid4().hex}",
            "payment_status": "open",
            "lines": [{"article_id": article_id, "qty": 3, "unit_cents": 500}],
        },
    }
    first = client.post("/edge/v1/sync/operational/chunk", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    second = client.post("/edge/v1/sync/operational/chunk", headers=headers, json=payload)
    assert second.status_code == 200, second.text

    db = SessionLocal()
    try:
        row = (
            db.query(EventArticleStock)
            .filter(EventArticleStock.event_id == event_id, EventArticleStock.article_id == article_id)
            .one()
        )
        assert row.in_stock == 17
    finally:
        db.close()
