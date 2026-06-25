"""Payment types reference API."""

from datetime import UTC

from app.database import SessionLocal
from app.main import app
from app.models import PaymentType, User
from app.roles import ROLE_MEMBER, ROLE_PLATFORM_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

client = TestClient(app)


def _token(email: str, password: str = "secret") -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _setup_users():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "pt-member@test.local").first():
            return
        member = User(
            email="pt-member@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        platform = User(
            email="pt-platform@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_PLATFORM_ADMIN,
            is_superuser=True,
        )
        db.add_all([member, platform])
        db.commit()
    finally:
        db.close()


def test_list_payment_types_seeded():
    _setup_users()
    headers = {"Authorization": f"Bearer {_token('pt-member@test.local')}"}
    r = client.get("/payment-types/", headers=headers)
    assert r.status_code == 200, r.text
    slugs = {row["slug"] for row in r.json()}
    assert "cash" in slugs
    assert "twint" in slugs


def test_platform_admin_can_create_payment_type():
    _setup_users()
    headers = {"Authorization": f"Bearer {_token('pt-platform@test.local')}"}
    created = client.post(
        "/payment-types/",
        headers=headers,
        json={"slug": "test_pay", "sort_order": 99, "is_active": True},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["slug"] == "test_pay"


def test_member_cannot_create_payment_type():
    _setup_users()
    headers = {"Authorization": f"Bearer {_token('pt-member@test.local')}"}
    r = client.post(
        "/payment-types/",
        headers=headers,
        json={"slug": "blocked", "sort_order": 0, "is_active": True},
    )
    assert r.status_code == 403, r.text


def test_delete_payment_type_in_use_by_event():
    from datetime import datetime

    from app.models import Event, HireCompany, Organisation

    _setup_users()
    db = SessionLocal()
    try:
        pt = db.query(PaymentType).filter(PaymentType.slug == "cash").first()
        assert pt is not None
        hc = HireCompany(name="PT HC", country_id=1)
        db.add(hc)
        db.flush()
        org = Organisation(name="PT Org", hire_company_id=hc.id, country_id=1, currency="EUR")
        db.add(org)
        db.flush()
        now = datetime.now(UTC)
        event = Event(
            name="PT Event",
            status="config",
            start=now,
            end=now,
            organisation_id=org.id,
            payment_types=["cash"],
        )
        db.add(event)
        db.commit()
        pt_id = pt.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {_token('pt-platform@test.local')}"}
    deleted = client.delete(f"/payment-types/{pt_id}", headers=headers)
    assert deleted.status_code == 400, deleted.text
