"""Rental container API: CRUD, assign, overlap, tenant isolation, fleet."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import Appliance, HireCompany, Organisation, User
from app.roles import ROLE_ORGANISATION_ADMIN, ROLE_TENANT_ADMIN
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import add_lending, country_id_by_code

client = TestClient(app)


def _token_for(email: str, password: str = "secret") -> str:
    r = client.post("/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _tenant_fixture(suffix: str, *, with_org_user: bool = False):
    suffix = f"{suffix}-{uuid4().hex}"
    db = SessionLocal()
    try:
        company = HireCompany(name=f"Rental Tenant {suffix}")
        other = HireCompany(name=f"Other Tenant {suffix}")
        db.add_all([company, other])
        db.flush()
        org = Organisation(
            name=f"FC St.Gallen {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=company.id,
            currency="CHF",
        )
        foreign_org = Organisation(
            name=f"Foreign Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=other.id,
            currency="CHF",
        )
        db.add_all([org, foreign_org])
        db.flush()
        admin = User(
            email=f"rental-admin-{suffix}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=company.id,
            is_superuser=False,
        )
        other_admin = User(
            email=f"other-admin-{suffix}@test.local",
            hashed_password=get_password_hash("secret"),
            role=ROLE_TENANT_ADMIN,
            hire_company_id=other.id,
            is_superuser=False,
        )
        pi = Appliance(hire_company_id=company.id, type="server", name="Pi-01")
        printer = Appliance(hire_company_id=company.id, type="printer", name="Drucker-01")
        db.add_all([admin, other_admin, pi, printer])
        org_user = None
        if with_org_user:
            org_user = User(
                email=f"org-user-{suffix}@test.local",
                hashed_password=get_password_hash("secret"),
                role=ROLE_ORGANISATION_ADMIN,
                hire_company_id=company.id,
                is_superuser=False,
            )
            org_user.organisations.append(org)
            db.add(org_user)
        db.commit()
        return {
            "email": admin.email,
            "other_email": other_admin.email,
            "org_user_email": org_user.email if org_user else None,
            "org_id": org.id,
            "foreign_org_id": foreign_org.id,
            "pi_id": pi.id,
            "printer_id": printer.id,
            "company_id": company.id,
        }
    finally:
        db.close()


def test_create_empty_rental_and_display_name_fallback():
    fx = _tenant_fixture("empty")
    token = _token_for(fx["email"])
    start = datetime.now(UTC).date() + timedelta(days=10)
    end = start + timedelta(days=3)

    response = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={"organisation_id": fx["org_id"], "start_date": start.isoformat(), "end_date": end.isoformat()},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["label"] is None
    assert body["display_name"].startswith("FC St.Gallen")
    assert body["filled"] is False
    assert body["lendings"] == []

    listed = client.get("/rentals/", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    assert any(row["id"] == body["id"] for row in listed.json())


def test_labelled_rental_uses_label_as_display_name():
    fx = _tenant_fixture("label")
    token = _token_for(fx["email"])
    start = datetime.now(UTC).date() + timedelta(days=20)
    end = start + timedelta(days=2)

    response = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "label": "Openair 2026",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["label"] == "Openair 2026"
    assert body["display_name"] == "Openair 2026"
    assert "FC St.Gallen" not in (body["label"] or "")


def test_create_rental_rejects_end_before_start():
    fx = _tenant_fixture("range")
    token = _token_for(fx["email"])
    start = datetime.now(UTC).date()
    response = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": start.isoformat(),
            "end_date": (start - timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 422


def test_create_rental_rejects_org_outside_tenant():
    fx = _tenant_fixture("foreign-org")
    token = _token_for(fx["email"])
    start = datetime.now(UTC).date()
    response = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["foreign_org_id"],
            "start_date": start.isoformat(),
            "end_date": start.isoformat(),
        },
    )
    assert response.status_code == 403
    listed = client.get("/rentals/", headers={"Authorization": f"Bearer {token}"})
    assert listed.json() == []


def test_list_rentals_scoped_to_active_verleiher():
    fx = _tenant_fixture("scope")
    token = _token_for(fx["email"])
    other = _token_for(fx["other_email"])
    start = datetime.now(UTC).date() + timedelta(days=5)
    created = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={"organisation_id": fx["org_id"], "start_date": start.isoformat(), "end_date": start.isoformat()},
    )
    assert created.status_code == 201
    rental_id = created.json()["id"]
    other_list = client.get("/rentals/", headers={"Authorization": f"Bearer {other}"})
    assert other_list.status_code == 200
    assert other_list.json() == []
    foreign = client.get(f"/rentals/{rental_id}", headers={"Authorization": f"Bearer {other}"})
    assert foreign.status_code in (403, 404)


def test_organisation_user_cannot_create_rental():
    fx = _tenant_fixture("org-user", with_org_user=True)
    token = _token_for(fx["org_user_email"])
    start = datetime.now(UTC).date()
    response = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={"organisation_id": fx["org_id"], "start_date": start.isoformat(), "end_date": start.isoformat()},
    )
    assert response.status_code == 403


def test_assign_inherits_rental_dates_and_overlap_rejected():
    fx = _tenant_fixture("assign")
    token = _token_for(fx["email"])
    start = datetime.now(UTC).date() + timedelta(days=30)
    end = start + timedelta(days=3)
    created = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={"organisation_id": fx["org_id"], "start_date": start.isoformat(), "end_date": end.isoformat()},
    )
    rental_id = created.json()["id"]
    assigned = client.post(
        f"/rentals/{rental_id}/appliances",
        headers={"Authorization": f"Bearer {token}"},
        json={"appliance_id": fx["pi_id"]},
    )
    assert assigned.status_code == 200, assigned.text
    lending = assigned.json()["lendings"][0]
    assert lending["start_date"] == start.isoformat()
    assert lending["end_date"] == end.isoformat()
    assert assigned.json()["filled"] is True

    other = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": (start + timedelta(days=1)).isoformat(),
            "end_date": (end + timedelta(days=1)).isoformat(),
        },
    )
    overlap = client.post(
        f"/rentals/{other.json()['id']}/appliances",
        headers={"Authorization": f"Bearer {token}"},
        json={"appliance_id": fx["pi_id"]},
    )
    assert overlap.status_code == 400
    assert overlap.json()["detail"]["code"] == "lending_overlap"
    assert client.get(f"/rentals/{other.json()['id']}", headers={"Authorization": f"Bearer {token}"}).json()["lendings"] == []


def test_handover_day_assign_allowed_interior_overlap_rejected():
    fx = _tenant_fixture("handover")
    token = _token_for(fx["email"])
    start = datetime.now(UTC).date() + timedelta(days=60)
    end = start + timedelta(days=4)
    first = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert first.status_code == 201, first.text

    handover = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": end.isoformat(),
            "end_date": (end + timedelta(days=3)).isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert handover.status_code == 201, handover.text
    assert len(handover.json()["lendings"]) == 1

    interior = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": (end - timedelta(days=1)).isoformat(),
            "end_date": (end + timedelta(days=2)).isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert interior.status_code == 400
    assert interior.json()["detail"]["code"] == "lending_overlap"


def test_return_day_allows_new_lending_same_day():
    fx = _tenant_fixture("return-day")
    token = _token_for(fx["email"])
    today = datetime.now(UTC).date()
    current = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=2)).isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert current.status_code == 201, current.text
    lending_id = current.json()["lendings"][0]["id"]
    returned = client.delete(
        f"/rentals/{current.json()['id']}/lendings/{lending_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["lendings"][0]["returned_at"] is not None

    again = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert again.status_code == 201, again.text
    assert again.json()["lendings"][0]["segment"] == "current"


def test_identical_one_day_windows_handover_allowed():
    fx = _tenant_fixture("same-day")
    token = _token_for(fx["email"])
    day = datetime.now(UTC).date() + timedelta(days=90)
    first = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert second.status_code == 201, second.text


def test_unassign_planned_and_return_current_keep_rental():
    fx = _tenant_fixture("unassign")
    token = _token_for(fx["email"])
    today = datetime.now(UTC).date()
    future_start = today + timedelta(days=40)
    future = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": future_start.isoformat(),
            "end_date": (future_start + timedelta(days=2)).isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert future.status_code == 201, future.text
    planned_id = future.json()["lendings"][0]["id"]
    removed = client.delete(
        f"/rentals/{future.json()['id']}/lendings/{planned_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert removed.status_code == 200
    assert removed.json()["lendings"] == []
    assert client.get(f"/rentals/{future.json()['id']}", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    current = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=2)).isoformat(),
            "appliance_ids": [fx["printer_id"]],
        },
    )
    lending_id = current.json()["lendings"][0]["id"]
    returned = client.delete(
        f"/rentals/{current.json()['id']}/lendings/{lending_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["lendings"][0]["returned_at"] is not None
    assert returned.json()["start_date"] == today.isoformat()


def test_delete_empty_and_planned_only_and_reject_current():
    fx = _tenant_fixture("delete")
    token = _token_for(fx["email"])
    today = datetime.now(UTC).date()
    empty = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": (today + timedelta(days=50)).isoformat(),
            "end_date": (today + timedelta(days=51)).isoformat(),
        },
    )
    assert client.delete(f"/rentals/{empty.json()['id']}", headers={"Authorization": f"Bearer {token}"}).status_code == 204

    planned = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": (today + timedelta(days=60)).isoformat(),
            "end_date": (today + timedelta(days=62)).isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert client.delete(f"/rentals/{planned.json()['id']}", headers={"Authorization": f"Bearer {token}"}).status_code == 204

    current = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
            "appliance_ids": [fx["printer_id"]],
        },
    )
    denied = client.delete(f"/rentals/{current.json()['id']}", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 400
    assert denied.json()["detail"]["code"] == "rental_has_current_lending"
    assert client.get(f"/rentals/{current.json()['id']}", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_patch_dates_updates_open_lendings_and_rolls_back_on_overlap():
    fx = _tenant_fixture("patch-dates")
    token = _token_for(fx["email"])
    today = datetime.now(UTC).date()
    start = today + timedelta(days=70)
    first = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=2)).isoformat(),
            "appliance_ids": [fx["pi_id"], fx["printer_id"]],
        },
    )
    assert first.status_code == 201, first.text
    blocker = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": (start + timedelta(days=10)).isoformat(),
            "end_date": (start + timedelta(days=12)).isoformat(),
            "appliance_ids": [fx["pi_id"]],
        },
    )
    assert blocker.status_code == 201, blocker.text

    extended = client.patch(
        f"/rentals/{first.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"end_date": (start + timedelta(days=3)).isoformat()},
    )
    assert extended.status_code == 200, extended.text
    assert all(row["end_date"] == (start + timedelta(days=3)).isoformat() for row in extended.json()["lendings"])

    collide = client.patch(
        f"/rentals/{first.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"end_date": (start + timedelta(days=11)).isoformat()},
    )
    assert collide.status_code == 400
    assert collide.json()["detail"]["code"] == "lending_overlap"
    still = client.get(f"/rentals/{first.json()['id']}", headers={"Authorization": f"Bearer {token}"}).json()
    assert still["end_date"] == (start + timedelta(days=3)).isoformat()
    assert still["organisation_id"] == fx["org_id"]

    # Organisation is not part of RentalUpdate; extra fields are ignored and org stays put.
    relabel = client.patch(
        f"/rentals/{first.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "Kept org", "organisation_id": fx["foreign_org_id"]},
    )
    assert relabel.status_code == 200, relabel.text
    assert relabel.json()["label"] == "Kept org"
    assert relabel.json()["organisation_id"] == fx["org_id"]


def test_floating_lending_create_rejected():
    fx = _tenant_fixture("floating")
    token = _token_for(fx["email"])
    today = datetime.now(UTC).date()
    response = client.post(
        f"/appliances/{fx['pi_id']}/lendings",
        headers={"Authorization": f"Bearer {token}"},
        json={"organisation_id": fx["org_id"], "start_date": today.isoformat(), "duration_days": 3},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "rental_required"


def test_create_with_appliance_ids_is_all_or_nothing():
    fx = _tenant_fixture("atomic")
    token = _token_for(fx["email"])
    today = datetime.now(UTC).date()
    start = today + timedelta(days=80)
    add_db = SessionLocal()
    try:
        add_lending(
            add_db,
            appliance_id=fx["pi_id"],
            organisation_id=fx["org_id"],
            start_date=start,
            end_date=start + timedelta(days=2),
            hire_company_id=fx["company_id"],
        )
        add_db.commit()
    finally:
        add_db.close()

    response = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=2)).isoformat(),
            "appliance_ids": [fx["pi_id"], fx["printer_id"]],
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "lending_overlap"
    listed = client.get(
        f"/rentals/?from={start.isoformat()}&to={(start + timedelta(days=2)).isoformat()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    # only the pre-existing one-device rental from add_lending, not a new empty/partial rental
    assert len(listed.json()) == 1
    assert listed.json()[0]["lendings"][0]["appliance_id"] == fx["pi_id"]


def test_fleet_groups_by_type_and_hides_empty_rentals():
    fx = _tenant_fixture("fleet")
    token = _token_for(fx["email"])
    start = date_in_next_month()
    end = start + timedelta(days=2)
    client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "label": "Openair 2026",
            "appliance_ids": [fx["pi_id"]],
        },
    )
    client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "organisation_id": fx["org_id"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
    )
    fleet = client.get(
        f"/rentals/fleet?year={start.year}&month={start.month}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fleet.status_code == 200, fleet.text
    groups = {g["type"]: g["appliances"] for g in fleet.json()["groups"]}
    assert "server" in groups
    assert "printer" in groups
    pi = next(a for a in groups["server"] if a["id"] == fx["pi_id"])
    assert pi["occupancies"][0]["display_name"] == "Openair 2026"
    printer = next(a for a in groups["printer"] if a["id"] == fx["printer_id"])
    assert printer["occupancies"] == []


def date_in_next_month():
    today = datetime.now(UTC).date()
    if today.month == 12:
        return today.replace(year=today.year + 1, month=1, day=1)
    return today.replace(month=today.month + 1, day=1)


def test_list_rentals_filters_by_organisation_id():
    fx = _tenant_fixture("org-filter")
    token = _token_for(fx["email"])
    start = datetime.now(UTC).date() + timedelta(days=15)
    end = start + timedelta(days=1)
    created = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={"organisation_id": fx["org_id"], "start_date": start.isoformat(), "end_date": end.isoformat()},
    )
    assert created.status_code == 201
    listed = client.get(
        f"/rentals/?organisation_id={fx['org_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert any(row["id"] == created.json()["id"] for row in listed.json())
    foreign = client.get(
        f"/rentals/?organisation_id={fx['foreign_org_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert foreign.status_code == 403
