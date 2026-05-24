"""Validation helpers for event stations, event waiters, and app layouts (UTC calendar overlap with lendings)."""

from __future__ import annotations

import uuid
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .models import (
    Appliance,
    ApplianceLending,
    Article,
    ArticleCategory,
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventCashRegister,
    EventStation,
    EventWaiter,
    Waiter,
)


PICKUP_PREFIX_RE = re.compile(r"^[A-Z]{1,3}$")


def event_printer_candidates(db: Session, event: Event) -> list[Appliance]:
    """Printers with open current or planned lendings to the event organisation (UTC calendar days)."""
    today = datetime.now(timezone.utc).date()
    rows = (
        db.query(Appliance)
        .join(ApplianceLending, ApplianceLending.appliance_id == Appliance.id)
        .filter(
            Appliance.type == "printer",
            ApplianceLending.organisation_id == event.organisation_id,
            ApplianceLending.returned_at.is_(None),
            ApplianceLending.end_date >= today,
        )
        .distinct()
        .order_by(Appliance.id)
        .all()
    )
    return rows


def assert_printer_eligible(db: Session, event: Event, appliance_id: int | None) -> None:
    if appliance_id is None:
        return
    allowed = {a.id for a in event_printer_candidates(db, event)}
    if appliance_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected printer is not available via a current or planned lending for this organisation",
        )


def article_ids_in_event_organisation(db: Session, event: Event, article_ids: list[int]) -> bool:
    if not article_ids:
        return True
    org_id = event.organisation_id
    count = (
        db.query(Article.id)
        .join(ArticleCategory, Article.article_category_id == ArticleCategory.id)
        .filter(
            Article.id.in_(article_ids),
            ArticleCategory.organisation_id == org_id,
        )
        .distinct()
        .count()
    )
    return count == len(set(article_ids))


def assert_station_articles_in_org(db: Session, event: Event, article_ids: list[int]) -> None:
    if not article_ids:
        return
    if not article_ids_in_event_organisation(db, event, article_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more articles are not in this event's organisation",
        )
    rows = db.query(Article.id, Article.is_addition).filter(Article.id.in_(list(set(article_ids)))).all()
    for aid, is_addition in rows:
        if is_addition:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Zusatz article {aid} cannot be assigned to a station",
            )


def station_article_union_from_payload(stations_payload: list) -> set[int]:
    out: set[int] = set()
    for st in stations_payload:
        ids = getattr(st, "article_ids", None) or []
        out.update(ids)
    return out


def assert_cell_articles_subset_of_stations(
    stations_payload: list,
    layouts_payload: list,
) -> None:
    allowed = station_article_union_from_payload(stations_payload)
    for layout in layouts_payload:
        for cell in layout.cells:
            for aid in cell.article_ids:
                if aid not in allowed:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Layout cell ({cell.row},{cell.col}) references article {aid} "
                            "that is not linked to any station for this event"
                        ),
                    )


def assert_source_waiter_in_org(db: Session, event: Event, source_waiter_id: int | None) -> None:
    if source_waiter_id is None:
        return
    w = db.query(Waiter).filter(Waiter.id == source_waiter_id).first()
    if not w or w.organisation_id != event.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_waiter_id must reference a waiter in the same organisation as the event",
        )


def assert_exactly_one_default_layout(layouts_payload: list) -> None:
    defaults = [lo for lo in layouts_payload if lo.is_default]
    if len(defaults) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Exactly one app layout must have is_default=true",
        )


def assert_cash_registers_valid(db: Session, event: Event, registers_payload: list, layouts_payload: list) -> None:
    layout_uuids = {
        str(getattr(lo, "uuid", "") or "").strip()
        for lo in layouts_payload
        if str(getattr(lo, "uuid", "") or "").strip()
    }
    for reg in registers_payload:
        prefix = str(getattr(reg, "pickup_code_prefix", "") or "").strip().upper()
        if not PICKUP_PREFIX_RE.match(prefix):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cash-register pickup prefix must contain 1-3 letters A-Z",
            )
        layout_uuid = str(getattr(reg, "layout_uuid", "") or "").strip()
        if layout_uuid not in layout_uuids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cash register must reference an app layout from this event",
            )
        assert_printer_eligible(db, event, getattr(reg, "receipt_printer_appliance_id", None))


def assert_layout_cells_within_grid(layouts_payload: list) -> None:
    for layout in layouts_payload:
        w, h = layout.grid_width, layout.grid_height
        seen: set[tuple[int, int]] = set()
        for cell in layout.cells:
            if not (0 <= cell.row < h and 0 <= cell.col < w):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Cell ({cell.row},{cell.col}) out of bounds for grid {w}x{h}",
                )
            key = (cell.row, cell.col)
            if key in seen:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Duplicate cell position ({cell.row},{cell.col}) in one layout",
                )
            seen.add(key)


def replace_event_configuration(
    db: Session,
    event: Event,
    *,
    stations_in: list,
    event_waiters_in: list,
    app_layouts_in: list,
    cash_registers_in: list | None = None,
) -> None:
    """Replace all configuration children. Caller must commit. Validates before mutating."""
    cash_registers_in = cash_registers_in or []
    for st in stations_in:
        assert_station_articles_in_org(db, event, list(st.article_ids))
        assert_printer_eligible(db, event, st.printer_appliance_id)
    for ew in event_waiters_in:
        assert_source_waiter_in_org(db, event, ew.source_waiter_id)

    assert_exactly_one_default_layout(app_layouts_in)
    assert_layout_cells_within_grid(app_layouts_in)
    assert_cell_articles_subset_of_stations(stations_in, app_layouts_in)
    assert_cash_registers_valid(db, event, cash_registers_in, app_layouts_in)

    # Delete existing (FK-safe order)
    layouts = db.query(EventAppLayout).filter(EventAppLayout.event_id == event.id).all()
    for layout in layouts:
        cells = db.query(EventAppLayoutCell).filter(EventAppLayoutCell.layout_id == layout.id).all()
        for cell in cells:
            cell.articles = []
            db.delete(cell)
        db.delete(layout)

    existing_stations = {
        st.uuid: st
        for st in db.query(EventStation).filter(EventStation.event_id == event.id).all()
    }
    kept_station_uuids: set[str] = set()
    for idx, st_in in enumerate(stations_in):
        st_uuid = (getattr(st_in, "uuid", None) or "").strip() or None
        st = existing_stations.get(st_uuid) if st_uuid else None
        if st is None:
            st = EventStation(
                event_id=event.id,
                uuid=st_uuid or str(uuid.uuid4()),
                name=st_in.name.strip(),
                sort_order=idx,
                printer_appliance_id=st_in.printer_appliance_id,
                kitchen_monitor_enabled=bool(getattr(st_in, "kitchen_monitor_enabled", False)),
            )
            db.add(st)
            db.flush()
        else:
            st.name = st_in.name.strip()
            st.sort_order = idx
            st.printer_appliance_id = st_in.printer_appliance_id
            st.kitchen_monitor_enabled = bool(getattr(st_in, "kitchen_monitor_enabled", False))
        kept_station_uuids.add(st.uuid)
        if st_in.article_ids:
            arts = db.query(Article).filter(Article.id.in_(list(set(st_in.article_ids)))).all()
            st.articles = arts
        else:
            st.articles = []

    for st_uuid, st in list(existing_stations.items()):
        if st_uuid not in kept_station_uuids:
            st.articles = []
            db.delete(st)
    db.flush()

    existing_waiters = {
        ew.uuid: ew
        for ew in db.query(EventWaiter).filter(EventWaiter.event_id == event.id).all()
    }
    kept_waiter_uuids: set[str] = set()
    for ew_in in event_waiters_in:
        ew_uuid = (getattr(ew_in, "uuid", None) or "").strip() or None
        ew = existing_waiters.get(ew_uuid) if ew_uuid else None
        if ew is None:
            ew = EventWaiter(
                event_id=event.id,
                uuid=ew_uuid or str(uuid.uuid4()),
                name=ew_in.name.strip(),
                pin=str(ew_in.pin),
                source_waiter_id=ew_in.source_waiter_id,
            )
            db.add(ew)
        else:
            ew.name = ew_in.name.strip()
            ew.pin = str(ew_in.pin)
            ew.source_waiter_id = ew_in.source_waiter_id
        kept_waiter_uuids.add(ew.uuid)

    for ew_uuid, ew in list(existing_waiters.items()):
        if ew_uuid not in kept_waiter_uuids:
            db.delete(ew)
    db.flush()

    for lo_in in app_layouts_in:
        lo = EventAppLayout(
            event_id=event.id,
            uuid=(getattr(lo_in, "uuid", None) or str(uuid.uuid4())),
            name=(lo_in.name or "").strip() or None,
            is_default=bool(lo_in.is_default),
            grid_width=lo_in.grid_width,
            grid_height=lo_in.grid_height,
        )
        db.add(lo)
        db.flush()
        for c in lo_in.cells:
            cell = EventAppLayoutCell(
                layout_id=lo.id,
                row=c.row,
                col=c.col,
                label=(c.label or "").strip(),
                color=(c.color or "#eeeeee").strip() or "#eeeeee",
            )
            db.add(cell)
            db.flush()
            if c.article_ids:
                arts = db.query(Article).filter(Article.id.in_(list(set(c.article_ids)))).all()
                cell.articles = arts

    existing_registers = {
        reg.uuid: reg
        for reg in db.query(EventCashRegister).filter(EventCashRegister.event_id == event.id).all()
    }
    kept_register_uuids: set[str] = set()
    for idx, reg_in in enumerate(cash_registers_in):
        reg_uuid = (getattr(reg_in, "uuid", None) or "").strip() or None
        reg = existing_registers.get(reg_uuid) if reg_uuid else None
        if reg is None:
            reg = EventCashRegister(event_id=event.id, uuid=reg_uuid or str(uuid.uuid4()))
            db.add(reg)
        reg.name = str(reg_in.name or "").strip()
        reg.sort_order = idx
        reg.pickup_code_prefix = str(reg_in.pickup_code_prefix or "").strip().upper()
        reg.pin = str(getattr(reg_in, "pin", None) or "0000").strip() or "0000"
        reg.layout_uuid = str(reg_in.layout_uuid or "").strip()
        reg.receipt_printer_appliance_id = getattr(reg_in, "receipt_printer_appliance_id", None)
        kept_register_uuids.add(reg.uuid)

    for reg_uuid, reg in list(existing_registers.items()):
        if reg_uuid not in kept_register_uuids:
            db.delete(reg)


def build_station_article_tree(db: Session, event: Event) -> list[dict]:
    """PrimeVue Tree nodes: categories under the event org; leaves only for articles on any station."""
    station_article_ids: set[int] = set()
    for st in event.stations:
        for a in st.articles:
            station_article_ids.add(a.id)
    if not station_article_ids:
        return []

    categories = (
        db.query(ArticleCategory)
        .options(joinedload(ArticleCategory.articles))
        .filter(ArticleCategory.organisation_id == event.organisation_id)
        .order_by(ArticleCategory.name)
        .all()
    )
    nodes: list[dict] = []
    for cat in categories:
        children = []
        for art in sorted(cat.articles, key=lambda x: (x.name or "").lower()):
            if art.id not in station_article_ids or art.is_addition:
                continue
            children.append(
                {
                    "key": f"art-{art.id}",
                    "label": f"{art.label} — {art.name}",
                    "selectable": True,
                    "leaf": True,
                    "data": {"article_id": art.id},
                }
            )
        if children:
            nodes.append(
                {
                    "key": f"cat-{cat.id}",
                    "label": cat.name,
                    "selectable": False,
                    "children": children,
                }
            )
    return nodes
