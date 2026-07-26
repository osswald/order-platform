"""Public Mietanfrage endpoint: validation, honeypot, mail, rate limit."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

VALID_PAYLOAD = {
    "name": "Anna Muster",
    "organisation": "Festverein Beispiel",
    "email": "anna@example.com",
    "phone": "+41 79 000 00 00",
    "timeframe": "12.–14. August 2026",
    "message": "Wir benötigen POS für unser Dorffest, ca. 4 Stationen.",
    "website": "",
}


@pytest.fixture
def inquiry_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("RENTAL_INQUIRY_TO", "kontakt@vendiqo.ch")
    return client


def test_valid_inquiry_triggers_send(inquiry_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    send = MagicMock()
    monkeypatch.setattr("app.routers.public_rental_inquiry.send_rental_inquiry_email", send)

    response = inquiry_client.post("/public/rental-inquiry", json=VALID_PAYLOAD)

    assert response.status_code == 204
    send.assert_called_once()
    kwargs = send.call_args.kwargs
    assert kwargs["name"] == "Anna Muster"
    assert kwargs["organisation"] == "Festverein Beispiel"
    assert kwargs["email"] == "anna@example.com"


def test_missing_required_field_rejected(inquiry_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    send = MagicMock()
    monkeypatch.setattr("app.routers.public_rental_inquiry.send_rental_inquiry_email", send)

    payload = {**VALID_PAYLOAD}
    del payload["message"]
    response = inquiry_client.post("/public/rental-inquiry", json=payload)

    assert response.status_code == 422
    send.assert_not_called()


def test_invalid_email_rejected(inquiry_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    send = MagicMock()
    monkeypatch.setattr("app.routers.public_rental_inquiry.send_rental_inquiry_email", send)

    response = inquiry_client.post(
        "/public/rental-inquiry",
        json={**VALID_PAYLOAD, "email": "not-an-email"},
    )

    assert response.status_code == 422
    send.assert_not_called()


def test_honeypot_filled_does_not_send(inquiry_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    send = MagicMock()
    monkeypatch.setattr("app.routers.public_rental_inquiry.send_rental_inquiry_email", send)

    response = inquiry_client.post(
        "/public/rental-inquiry",
        json={**VALID_PAYLOAD, "website": "http://spam.example"},
    )

    assert response.status_code == 204
    send.assert_not_called()


def test_rate_limit_returns_429(inquiry_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    send = MagicMock()
    monkeypatch.setattr("app.routers.public_rental_inquiry.send_rental_inquiry_email", send)

    statuses = [
        inquiry_client.post("/public/rental-inquiry", json=VALID_PAYLOAD).status_code
        for _ in range(6)
    ]

    assert 429 in statuses
    assert all(code in (204, 429) for code in statuses)


def test_mail_error_returns_503(inquiry_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.rental_inquiry_mail import RentalInquiryMailError

    def _raise(**_kwargs):
        raise RentalInquiryMailError("smtp unavailable")

    monkeypatch.setattr("app.routers.public_rental_inquiry.send_rental_inquiry_email", _raise)

    response = inquiry_client.post("/public/rental-inquiry", json=VALID_PAYLOAD)

    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["code"] == "rental_inquiry_mail_unavailable"
