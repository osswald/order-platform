"""Organisation color palette for app layout buttons."""

from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import HireCompany, Organisation, User
from app.roles import ROLE_MEMBER, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import country_id_by_code

client = TestClient(app)


def _seed_tenant() -> int:
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"ColorPalette HC {uuid4().hex[:8]}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name="ColorPalette Org",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        db.add(
            User(
                email=f"colorpalette-{uuid4().hex[:8]}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return org.id
    finally:
        db.close()


def _token() -> str:
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter(User.email.like("colorpalette-%@test.local"))
            .order_by(User.id.desc())
            .first()
        )
        email = user.email
    finally:
        db.close()
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _seed_member_without_manage(org_id: int) -> str:
    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        member = User(
            email=f"colorpalette-member-{uuid4().hex[:8]}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_MEMBER,
        )
        member.organisations = [org]
        db.add(member)
        db.commit()
        email = member.email
    finally:
        db.close()
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_color_palette_empty_by_default():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    response = client.get(f"/organisations/{org_id}/color-palette", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {"colors": []}


def test_color_palette_put_round_trip_normalizes_hex():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    saved = client.put(
        f"/organisations/{org_id}/color-palette",
        headers=headers,
        json={
            "colors": [
                {"label": "Primary", "color": "#f00"},
                {"label": "Secondary", "color": "#00ff00"},
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    data = saved.json()
    assert data["colors"] == [
        {"label": "Primary", "color": "#FF0000"},
        {"label": "Secondary", "color": "#00FF00"},
    ]

    loaded = client.get(f"/organisations/{org_id}/color-palette", headers=headers)
    assert loaded.status_code == 200
    assert loaded.json() == data


def test_color_palette_validation_errors():
    org_id = _seed_tenant()
    headers = {"Authorization": f"Bearer {_token()}"}

    bad_hex = client.put(
        f"/organisations/{org_id}/color-palette",
        headers=headers,
        json={"colors": [{"label": "Bad", "color": "red"}]},
    )
    assert bad_hex.status_code == 422

    empty_label = client.put(
        f"/organisations/{org_id}/color-palette",
        headers=headers,
        json={"colors": [{"label": "   ", "color": "#FF0000"}]},
    )
    assert empty_label.status_code == 422

    duplicate_colors = client.put(
        f"/organisations/{org_id}/color-palette",
        headers=headers,
        json={
            "colors": [
                {"label": "A", "color": "#FF0000"},
                {"label": "B", "color": "#ff0000"},
            ]
        },
    )
    assert duplicate_colors.status_code == 422

    too_many = client.put(
        f"/organisations/{org_id}/color-palette",
        headers=headers,
        json={
            "colors": [
                {"label": f"Color {i}", "color": f"#{i:06x}"}
                for i in range(33)
            ]
        },
    )
    assert too_many.status_code == 422


def test_color_palette_put_forbidden_for_member():
    org_id = _seed_tenant()
    member_token = _seed_member_without_manage(org_id)
    headers = {"Authorization": f"Bearer {member_token}"}

    response = client.put(
        f"/organisations/{org_id}/color-palette",
        headers=headers,
        json={"colors": [{"label": "Primary", "color": "#FF0000"}]},
    )
    assert response.status_code == 403
