"""Deferred ESC/POS render contexts for queued network PrintJobs."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from .bundle_cache import event_from_bundle, get_bundle_dict_raw
from .models import PrintJob

log = logging.getLogger(__name__)

RENDER_CONTEXT_VERSION = 1


def make_render_context(*, kind: str, **fields: Any) -> dict[str, Any]:
    ctx: dict[str, Any] = {"v": RENDER_CONTEXT_VERSION, "kind": kind}
    ctx.update(fields)
    return ctx


def dump_render_context(ctx: dict[str, Any]) -> str:
    return json.dumps(ctx, separators=(",", ":"))


def _article_map(ev: dict) -> dict:
    """Bundle events store articles as an id→article map (same as edge_common)."""
    arts = ev.get("articles") or {}
    return arts if isinstance(arts, dict) else {}


def load_event_for_print_job(db: Session, job: PrintJob) -> dict | None:
    """Resolve event for a job from render context or linked order."""
    event_id: int | None = None
    if job.render_context_json:
        try:
            ctx = json.loads(job.render_context_json)
            if isinstance(ctx, dict) and ctx.get("event_id") is not None:
                event_id = int(ctx["event_id"])
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    if event_id is None and job.local_order_id:
        from .models import LocalOrder

        order = db.query(LocalOrder).filter(LocalOrder.id == job.local_order_id).first()
        if order is not None:
            event_id = int(order.event_id)
    if event_id is None:
        return None
    bundle = get_bundle_dict_raw(db)
    if not bundle:
        return None
    return event_from_bundle(bundle, event_id)


def build_escpos_from_render_context(ctx: dict[str, Any], ev: dict | None) -> bytes:
    """Build ESC/POS bytes from a versioned render context + event dict."""
    # Lazy import: print_worker may call into this module from the worker loop.
    from .print_worker import (
        build_customer_pickup_text,
        build_escpos_receipt_text,
        build_payment_receipt_text,
        build_voucher_slip_text,
    )

    if int(ctx.get("v") or 0) != RENDER_CONTEXT_VERSION:
        raise ValueError(f"unsupported render context version: {ctx.get('v')!r}")
    kind = str(ctx.get("kind") or "")
    if not ev:
        raise ValueError("event required to render print job")
    event_name = str(ctx.get("event_name") or ev.get("name") or "Event")
    currency = str(ctx.get("currency") or ev.get("currency") or "EUR")
    feed_lines = int(ctx.get("feed_lines") or 1)
    arts = _article_map(ev)

    if kind in ("station_order", "kitchen_ticket"):
        payload = ctx.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("station render context missing payload")
        return build_escpos_receipt_text(
            payload,
            event_name,
            station_name=ctx.get("station_name"),
            articles=arts,
            local_order_id=ctx.get("local_order_id"),
            currency=currency,
            event=ev,
            feed_lines=feed_lines,
        )
    if kind == "customer_pickup":
        payload = ctx.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("customer_pickup render context missing payload")
        return build_customer_pickup_text(
            payload,
            event_name,
            station_name=ctx.get("station_name"),
            articles=arts,
            event=ev,
            local_order_id=ctx.get("local_order_id"),
            currency=currency,
            feed_lines=feed_lines,
        )
    if kind == "voucher":
        return build_voucher_slip_text(
            event_name=event_name,
            voucher_name=str(ctx.get("voucher_name") or "Gutschein"),
            value_cents=int(ctx.get("value_cents") or 0),
            currency=currency,
            copy_index=ctx.get("copy_index"),
            copy_total=ctx.get("copy_total"),
            event=ev,
            feed_lines=feed_lines,
        )
    if kind == "payment_receipt":
        payload = ctx.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("payment_receipt render context missing payload")
        return build_payment_receipt_text(
            payload,
            event_name,
            payment_id=ctx.get("payment_id"),
            articles=arts,
            currency=currency,
            generated_at=ctx.get("generated_at"),
            event=ev,
            feed_lines=feed_lines,
            paper_width=ctx.get("paper_width"),
            line_width=ctx.get("line_width"),
            charset=ctx.get("charset"),
        )
    raise ValueError(f"unsupported render context kind: {kind!r}")


def ensure_print_job_payload(db: Session, job: PrintJob, ev: dict | None = None) -> bytes:
    """Ensure job.escpos_payload is populated; return decoded ESC/POS bytes."""
    import base64

    if job.escpos_payload:
        return base64.b64decode(job.escpos_payload)
    if not job.render_context_json:
        raise ValueError("print job has empty escpos_payload and no render_context_json")
    try:
        ctx = json.loads(job.render_context_json)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid render_context_json") from exc
    if not isinstance(ctx, dict):
        raise ValueError("render_context_json must be an object")
    event = ev if ev is not None else load_event_for_print_job(db, job)
    raw = build_escpos_from_render_context(ctx, event)
    job.escpos_payload = base64.b64encode(raw).decode("ascii")
    return raw
