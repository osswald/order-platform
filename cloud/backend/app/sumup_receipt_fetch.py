"""Fetch and attach SumUp card receipt fields onto checkout rows."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from . import sumup_client
from .models import Organisation, SumupCheckout
from .sumup_receipt_info import receipt_info_from_transaction
from .sumup_tokens import get_valid_access_token

logger = logging.getLogger(__name__)


def checkout_receipt_info(row: SumupCheckout) -> dict[str, str] | None:
    raw = getattr(row, "receipt_info_json", None)
    if isinstance(raw, dict) and raw:
        return {str(k): str(v) for k, v in raw.items() if str(v).strip()}
    return None


def ensure_checkout_receipt_info(
    db: Session,
    organisation: Organisation,
    row: SumupCheckout,
) -> dict[str, str] | None:
    """When checkout is paid, fetch Transactions API details once and store them.

    Failures are logged and ignored so payment completion is never blocked.
    """
    existing = checkout_receipt_info(row)
    if existing:
        return existing
    if (row.status or "").lower() != "paid":
        return None
    txn_id = (row.sumup_transaction_id or "").strip()
    if not txn_id:
        return None
    merchant_code = (organisation.sumup_merchant_code or "").strip()
    if not merchant_code:
        return None
    try:
        access_token = get_valid_access_token(db, organisation)
        info: dict[str, str] = {}
        try:
            payload = sumup_client.get_transaction(
                access_token,
                merchant_code,
                client_transaction_id=txn_id,
            )
            info = receipt_info_from_transaction(payload)
        except Exception:
            logger.info(
                "SumUp receipt lookup by client_transaction_id failed for %s; trying id",
                txn_id,
                exc_info=True,
            )
        if not info:
            payload = sumup_client.get_transaction(
                access_token,
                merchant_code,
                transaction_id=txn_id,
            )
            info = receipt_info_from_transaction(payload)
        if info:
            row.receipt_info_json = info
            return info
    except Exception:
        logger.exception(
            "Failed to fetch SumUp receipt info for checkout %s txn %s",
            row.sumup_checkout_id,
            txn_id,
        )
    return None


def receipt_info_payload(row: SumupCheckout) -> dict[str, Any] | None:
    info = checkout_receipt_info(row)
    return dict(info) if info else None
