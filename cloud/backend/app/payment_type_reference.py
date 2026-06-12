"""Reference-data helpers for payment types."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from fastapi import status

from .i18n.errors import api_error
from .models import AccountingAccountPaymentTypeDefault, Event, PaymentType


def assert_payment_type_deletable(db: Session, payment_type: PaymentType) -> None:
    slug = payment_type.slug
    events = db.query(Event.id, Event.payment_types).all()
    for _event_id, payment_types in events:
        raw = payment_types
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (TypeError, ValueError):
                continue
        if isinstance(raw, list) and slug in [str(t).strip().lower() for t in raw]:
            raise api_error("payment_type_in_use", status.HTTP_400_BAD_REQUEST)
    if (
        db.query(AccountingAccountPaymentTypeDefault.id)
        .filter(AccountingAccountPaymentTypeDefault.payment_type_id == payment_type.id)
        .first()
        is not None
    ):
        raise api_error("payment_type_in_use", status.HTTP_400_BAD_REQUEST)


def get_payment_type_or_404(db: Session, payment_type_id: int) -> PaymentType:
    payment_type = db.query(PaymentType).filter(PaymentType.id == payment_type_id).first()
    if not payment_type:
        raise api_error("payment_type_not_found", status.HTTP_404_NOT_FOUND)
    return payment_type
