"""Persist order lines as normalized items (optional enrichment)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from ..models_operational import OrderItem


def _line_key(line: dict) -> str:
    raw = json.dumps(
        {
            "article_id": line.get("article_id"),
            "note": line.get("note") or "",
            "additions": line.get("additions") or [],
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def upsert_items_from_payload(
    db: Session,
    *,
    session_id: int,
    submission_id: int,
    event_id: int,
    table_number: int | None,
    collective_batch_id: int | None,
    lines: list[dict],
    order_number: int | None = None,
    ordered_at: datetime | None = None,
) -> None:
    for line in lines:
        if not isinstance(line, dict):
            continue
        article_id = line.get("article_id")
        if article_id is None and not line.get("voucher_definition_uuid"):
            continue
        qty = max(1, int(line.get("qty") or line.get("quantity") or 1))
        unit = int(line.get("unit_cents") or line.get("unit_price_cents") or 0)
        db.add(
            OrderItem(
                session_id=session_id,
                submission_id=submission_id,
                event_id=event_id,
                article_id=int(article_id) if article_id is not None else None,
                quantity=qty,
                unit_price_cents=unit,
                article_name=str(line.get("article_name") or ""),
                note=str(line.get("note") or ""),
                additions_json=json.dumps(line.get("additions") or []),
                station_uuid=line.get("station_uuid"),
                origin_table_number=table_number,
                current_table_number=table_number,
                order_number=order_number,
                ordered_at=ordered_at,
                status="OPEN",
                client_line_key=_line_key(line),
                collective_batch_id=collective_batch_id,
            )
        )
