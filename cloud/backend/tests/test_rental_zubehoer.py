"""Rental Zubehör catalog, rental lines, and packing-list PDF."""

from datetime import UTC, datetime, timedelta
from io import BytesIO

from app.main import app
from fastapi.testclient import TestClient
from pypdf import PdfReader

from tests.test_rentals_api import _tenant_fixture, _token_for

client = TestClient(app)


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _create_rental(token: str, org_id: int, *, start=None, end=None) -> dict:
    start = start or (datetime.now(UTC).date() + timedelta(days=10))
    end = end or start
    response = client.post(
        "/rentals/",
        headers={"Authorization": f"Bearer {token}"},
        json={"organisation_id": org_id, "start_date": start.isoformat(), "end_date": end.isoformat()},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_catalog_item(token: str, name: str, *, default_quantity=None) -> dict:
    payload = {"name": name, "sort_order": 0, "is_active": True}
    if default_quantity is not None:
        payload["default_quantity"] = default_quantity
    response = client.post(
        "/rental-zubehoer-catalog/",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_catalog_crud_tenant_scoped():
    fx = _tenant_fixture("zubehoer-catalog")
    token = _token_for(fx["email"])
    other = _token_for(fx["other_email"])

    created = _create_catalog_item(token, "Thermopapier", default_quantity=2)
    assert created["name"] == "Thermopapier"
    assert created["default_quantity"] == 2

    listed = client.get("/rental-zubehoer-catalog/", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    other_list = client.get("/rental-zubehoer-catalog/", headers={"Authorization": f"Bearer {other}"})
    assert other_list.status_code == 200
    assert other_list.json() == []

    updated = client.patch(
        f"/rental-zubehoer-catalog/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Thermorollen"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Thermorollen"

    deleted = client.delete(
        f"/rental-zubehoer-catalog/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted.status_code == 204
    assert client.get("/rental-zubehoer-catalog/", headers={"Authorization": f"Bearer {token}"}).json() == []


def test_catalog_default_quantity_optional():
    fx = _tenant_fixture("zubehoer-qty-opt")
    token = _token_for(fx["email"])
    created = _create_catalog_item(token, "Netzwerkkabel")
    assert created["default_quantity"] is None


def test_new_rental_has_no_zubehoer_lines():
    fx = _tenant_fixture("zubehoer-empty-rental")
    token = _token_for(fx["email"])
    rental = _create_rental(token, fx["org_id"])
    assert rental.get("zubehoer_lines") == []


def test_add_line_from_catalog_snapshots_label_and_default_quantity():
    fx = _tenant_fixture("zubehoer-pick")
    token = _token_for(fx["email"])
    catalog = _create_catalog_item(token, "Thermopapier", default_quantity=2)
    rental = _create_rental(token, fx["org_id"])

    line = client.post(
        f"/rentals/{rental['id']}/zubehoer-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"catalog_item_id": catalog["id"]},
    )
    assert line.status_code == 201, line.text
    body = line.json()
    assert body["label"] == "Thermopapier"
    assert body["quantity"] == 2
    assert body["catalog_item_id"] == catalog["id"]

    client.patch(
        f"/rental-zubehoer-catalog/{catalog['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Renamed"},
    )
    detail = client.get(f"/rentals/{rental['id']}", headers={"Authorization": f"Bearer {token}"})
    assert detail.json()["zubehoer_lines"][0]["label"] == "Thermopapier"


def test_add_line_from_catalog_allows_quantity_override():
    fx = _tenant_fixture("zubehoer-qty-override")
    token = _token_for(fx["email"])
    catalog = _create_catalog_item(token, "Thermopapier", default_quantity=2)
    rental = _create_rental(token, fx["org_id"])
    line = client.post(
        f"/rentals/{rental['id']}/zubehoer-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"catalog_item_id": catalog["id"], "quantity": 7},
    )
    assert line.status_code == 201, line.text
    assert line.json()["quantity"] == 7
    assert line.json()["label"] == "Thermopapier"


def test_free_text_line_without_catalog():
    fx = _tenant_fixture("zubehoer-free")
    token = _token_for(fx["email"])
    rental = _create_rental(token, fx["org_id"])
    line = client.post(
        f"/rentals/{rental['id']}/zubehoer-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "Verlängerungskabel 5m", "quantity": 3},
    )
    assert line.status_code == 201, line.text
    body = line.json()
    assert body["catalog_item_id"] is None
    assert body["label"] == "Verlängerungskabel 5m"
    assert body["quantity"] == 3


def test_line_quantity_may_be_omitted():
    fx = _tenant_fixture("zubehoer-no-qty")
    token = _token_for(fx["email"])
    rental = _create_rental(token, fx["org_id"])
    line = client.post(
        f"/rentals/{rental['id']}/zubehoer-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "Kabelbinder"},
    )
    assert line.status_code == 201, line.text
    assert line.json()["quantity"] is None


def test_org_user_forbidden_catalog_and_lines_and_pdf():
    fx = _tenant_fixture("zubehoer-org", with_org_user=True)
    admin = _token_for(fx["email"])
    org_token = _token_for(fx["org_user_email"])
    rental = _create_rental(admin, fx["org_id"])

    assert client.get("/rental-zubehoer-catalog/", headers={"Authorization": f"Bearer {org_token}"}).status_code == 403
    assert (
        client.post(
            f"/rentals/{rental['id']}/zubehoer-lines",
            headers={"Authorization": f"Bearer {org_token}"},
            json={"label": "X"},
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/rentals/{rental['id']}/packing-list.pdf",
            headers={"Authorization": f"Bearer {org_token}"},
        ).status_code
        == 403
    )


def test_zubehoer_lines_crud_on_rental():
    fx = _tenant_fixture("zubehoer-lines-crud")
    token = _token_for(fx["email"])
    rental = _create_rental(token, fx["org_id"])
    created = client.post(
        f"/rentals/{rental['id']}/zubehoer-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "Item A", "quantity": 1},
    )
    line_id = created.json()["id"]

    updated = client.patch(
        f"/rentals/{rental['id']}/zubehoer-lines/{line_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"quantity": 5},
    )
    assert updated.status_code == 200
    assert updated.json()["quantity"] == 5

    deleted = client.delete(
        f"/rentals/{rental['id']}/zubehoer-lines/{line_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deleted.status_code == 204
    detail = client.get(f"/rentals/{rental['id']}", headers={"Authorization": f"Bearer {token}"})
    assert detail.json()["zubehoer_lines"] == []


def test_delete_rental_with_zubehoer_lines():
    fx = _tenant_fixture("delete-zubehoer")
    token = _token_for(fx["email"])
    catalog = _create_catalog_item(token, "Kabel")
    rental = _create_rental(token, fx["org_id"])
    client.post(
        f"/rentals/{rental['id']}/zubehoer-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"catalog_item_id": catalog["id"]},
    )
    assert client.delete(f"/rentals/{rental['id']}", headers={"Authorization": f"Bearer {token}"}).status_code == 204
    assert client.get(f"/rentals/{rental['id']}", headers={"Authorization": f"Bearer {token}"}).status_code == 404


def test_packing_pdf_lists_open_lendings_only():
    fx = _tenant_fixture("zubehoer-pdf-lendings")
    token = _token_for(fx["email"])
    today = datetime.now(UTC).date()
    rental = _create_rental(token, fx["org_id"], start=today, end=today + timedelta(days=3))
    assigned = client.post(
        f"/rentals/{rental['id']}/appliances",
        headers={"Authorization": f"Bearer {token}"},
        json={"appliance_id": fx["pi_id"]},
    )
    lending_id = assigned.json()["lendings"][0]["id"]
    client.delete(
        f"/rentals/{rental['id']}/lendings/{lending_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        f"/rentals/{rental['id']}/appliances",
        headers={"Authorization": f"Bearer {token}"},
        json={"appliance_id": fx["printer_id"]},
    )

    response = client.get(
        f"/rentals/{rental['id']}/packing-list.pdf",
        headers={"Authorization": f"Bearer {token}", "Accept-Language": "de"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    text = _pdf_text(response.content)
    assert "Pi-01" not in text
    assert "Drucker-01" in text
    assert "Drucker" in text
    assert "192.168.1.50" in text


def test_packing_pdf_uses_localized_type_labels_and_type_order():
    fx = _tenant_fixture("zubehoer-pdf-order")
    token = _token_for(fx["email"])
    today = datetime.now(UTC).date()
    rental = _create_rental(token, fx["org_id"], start=today, end=today + timedelta(days=2))
    client.post(
        f"/rentals/{rental['id']}/appliances",
        headers={"Authorization": f"Bearer {token}"},
        json={"appliance_id": fx["printer_id"]},
    )
    client.post(
        f"/rentals/{rental['id']}/appliances",
        headers={"Authorization": f"Bearer {token}"},
        json={"appliance_id": fx["pi_id"]},
    )
    response = client.get(
        f"/rentals/{rental['id']}/packing-list.pdf",
        headers={"Authorization": f"Bearer {token}", "Accept-Language": "de"},
    )
    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Pi-01 (Server)" in text
    assert "Drucker-01 (Drucker, 192.168.1.50)" in text
    assert text.index("Pi-01") < text.index("Drucker-01")


def test_packing_pdf_zubehoer_quantity_only_when_set():
    fx = _tenant_fixture("zubehoer-pdf-qty")
    token = _token_for(fx["email"])
    rental = _create_rental(token, fx["org_id"])
    client.post(
        f"/rentals/{rental['id']}/zubehoer-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "Thermopapier", "quantity": 2},
    )
    client.post(
        f"/rentals/{rental['id']}/zubehoer-lines",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "Netzwerkkabel"},
    )

    response = client.get(
        f"/rentals/{rental['id']}/packing-list.pdf",
        headers={"Authorization": f"Bearer {token}", "Accept-Language": "de"},
    )
    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Thermopapier" in text
    assert "Netzwerkkabel" in text
    assert "Zubehör" in text
    # Quantity 2 appears; no placeholder dash for line without quantity
    assert "—" not in text
    thermo_idx = text.index("Thermopapier")
    cable_idx = text.index("Netzwerkkabel")
    assert "2" in text[thermo_idx : cable_idx]


def test_packing_pdf_has_no_prices():
    fx = _tenant_fixture("zubehoer-pdf-no-price")
    token = _token_for(fx["email"])
    rental = _create_rental(token, fx["org_id"])
    response = client.get(
        f"/rentals/{rental['id']}/packing-list.pdf",
        headers={"Authorization": f"Bearer {token}", "Accept-Language": "de"},
    )
    text = _pdf_text(response.content)
    assert "CHF" not in text
    assert "Einzelpreis" not in text
