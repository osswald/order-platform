"""SumUp webhook endpoint for checkout status updates."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from ..db_errors import commit_or_raise
from ..deps import get_db
from ..i18n.errors import api_error
from ..models import SumupCheckout, SumupWebhookEvent
from ..sumup_checkout_state import apply_checkout_payload, normalize_checkout_status

router = APIRouter()
logger = logging.getLogger(__name__)


def _webhook_secret() -> str:
    secret = (os.getenv("SUMUP_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise api_error("sumup_webhook_secret_missing", status.HTTP_503_SERVICE_UNAVAILABLE)
    return secret


def _verify_webhook_secret(request: Request) -> None:
    """Verify shared secret header.

    TODO: SumUp also supports `x-payload-signature` HMAC SHA-256 over the raw body;
    switch to that verification when webhook payloads are exercised in staging.
    """
    expected = _webhook_secret()
    provided = (request.headers.get("X-SumUp-Webhook-Secret") or "").strip()
    if not provided or provided != expected:
        raise api_error("sumup_webhook_invalid_secret", status.HTTP_401_UNAUTHORIZED)


def _event_id_from_payload(payload: dict[str, Any]) -> str:
    for key in ("id", "event_id", "webhook_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return json.dumps(payload, sort_keys=True)


@router.post("/webhooks")
async def sumup_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    _verify_webhook_secret(request)
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except json.JSONDecodeError as exc:
        raise api_error("sumup_invalid_payload", status.HTTP_400_BAD_REQUEST) from exc
    if not isinstance(payload, dict):
        raise api_error("sumup_invalid_payload", status.HTTP_400_BAD_REQUEST)

    event_id = _event_id_from_payload(payload)
    existing = (
        db.query(SumupWebhookEvent)
        .filter(SumupWebhookEvent.webhook_event_id == event_id)
        .first()
    )
    if existing:
        return {"received": "true", "duplicate": "true"}

    checkout_id = str(payload.get("checkout_id") or payload.get("id") or "").strip()
    # Solo Cloud API callbacks nest fields under ``data`` / ``payload``.
    nested = payload.get("data") if isinstance(payload.get("data"), dict) else None
    if not checkout_id and nested:
        checkout_id = str(nested.get("checkout_id") or nested.get("id") or "").strip()
    event_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else None
    if not checkout_id and event_payload:
        checkout_id = str(event_payload.get("checkout_id") or event_payload.get("id") or "").strip()
    event_type = str(payload.get("event_type") or payload.get("type") or "unknown")
    db.add(
        SumupWebhookEvent(
            webhook_event_id=event_id,
            event_type=event_type,
            sumup_checkout_id=checkout_id or None,
            payload_json=payload,
        )
    )

    status_source = event_payload or nested or payload
    if checkout_id:
        row = db.query(SumupCheckout).filter(SumupCheckout.sumup_checkout_id == checkout_id).first()
        if row:
            status_value = normalize_checkout_status(str(status_source.get("status")))
            row.status = status_value
            apply_checkout_payload(row, status_source)

    commit_or_raise(db)
    return {"received": "true"}
