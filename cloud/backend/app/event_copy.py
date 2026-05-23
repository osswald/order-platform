"""Duplicate an event configuration without sales or collective-bill data."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session, joinedload

from .event_config_validation import replace_event_configuration
from .models import (
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventArticleStock,
    EventStation,
    EventWaiter,
)
from .payment_types_config import payment_types_from_event
from .stock import upsert_stock_rows


def _load_event_for_copy(db: Session, event_id: int) -> Event | None:
    return (
        db.query(Event)
        .options(
            joinedload(Event.organisation),
            joinedload(Event.stations).joinedload(EventStation.articles),
            joinedload(Event.event_waiters),
            joinedload(Event.app_layouts).joinedload(EventAppLayout.cells).joinedload(EventAppLayoutCell.articles),
        )
        .filter(Event.id == event_id)
        .first()
    )


def _stations_payload(event: Event) -> list:
    out = []
    for st in sorted(event.stations, key=lambda s: (s.sort_order, s.id)):
        out.append(
            SimpleNamespace(
                uuid=None,
                name=st.name,
                printer_appliance_id=st.printer_appliance_id,
                kitchen_monitor_enabled=bool(getattr(st, "kitchen_monitor_enabled", False)),
                article_ids=[a.id for a in st.articles],
            )
        )
    return out


def _waiters_payload(event: Event) -> list:
    return [
        SimpleNamespace(
            uuid=None,
            name=ew.name,
            pin=ew.pin,
            source_waiter_id=ew.source_waiter_id,
        )
        for ew in sorted(event.event_waiters, key=lambda w: w.id)
    ]


def _layouts_payload(event: Event) -> list:
    out = []
    for lo in sorted(event.app_layouts, key=lambda x: x.id):
        cells = []
        for cell in sorted(lo.cells, key=lambda c: (c.row, c.col)):
            cells.append(
                SimpleNamespace(
                    row=cell.row,
                    col=cell.col,
                    label=cell.label or "",
                    color=cell.color or "#eeeeee",
                    article_ids=[a.id for a in cell.articles],
                )
            )
        out.append(
            SimpleNamespace(
                name=lo.name,
                is_default=bool(lo.is_default),
                grid_width=lo.grid_width,
                grid_height=lo.grid_height,
                cells=cells,
            )
        )
    return out


def default_copy_name(source_name: str) -> str:
    base = (source_name or "").strip() or "Event"
    suffix = " (Kopie)"
    if base.endswith(suffix):
        return base
    return f"{base}{suffix}"


def copy_event(db: Session, source: Event, *, name: str) -> Event:
    """Clone event config onto a new Event row. Caller must have loaded source relations."""
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")

    new_event = Event(
        name=name,
        status="config",
        start=source.start,
        end=source.end,
        currency=source.currency,
        organisation_id=source.organisation_id,
        payment_mode=getattr(source, "payment_mode", None) or "pay_later",
        payment_types=list(payment_types_from_event(source)),
    )
    if source.twint_qr_mime and source.twint_qr_data:
        new_event.twint_qr_mime = source.twint_qr_mime
        new_event.twint_qr_data = source.twint_qr_data

    db.add(new_event)
    db.flush()

    source_stock = (
        db.query(EventArticleStock).filter(EventArticleStock.event_id == source.id).all()
    )
    stock_by_article = {r.article_id: r for r in source_stock}

    replace_event_configuration(
        db,
        new_event,
        stations_in=_stations_payload(source),
        event_waiters_in=_waiters_payload(source),
        app_layouts_in=_layouts_payload(source),
    )

    from .additions import event_stock_article_ids

    allowed = event_stock_article_ids(db, new_event)
    stock_items = []
    for aid in sorted(allowed):
        row = stock_by_article.get(aid)
        if not row:
            continue
        stock_items.append(
            {
                "article_id": aid,
                "monitor_stock": row.monitor_stock,
                "in_stock": row.in_stock,
            }
        )
    if stock_items:
        upsert_stock_rows(db, new_event, stock_items)

    db.flush()
    return new_event
