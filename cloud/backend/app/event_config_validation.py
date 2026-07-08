"""Validation helpers for event stations, event waiters, and app layouts (UTC calendar overlap with lendings)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date

from fastapi import status
from sqlalchemy.orm import Session, joinedload

from .i18n.errors import api_error
from .models import (
    Appliance,
    ApplianceLending,
    Article,
    ArticleCategory,
    Event,
    EventAppLayout,
    EventAppLayoutCell,
    EventCashRegister,
    EventKitchenMonitorPrinter,
    EventStation,
    EventStationPrinterRule,
    EventWaiter,
    Waiter,
)
from .vouchers import assert_layout_cells_vouchers, normalize_cell_voucher_uuids, replace_event_voucher_definitions

PICKUP_PREFIX_RE = re.compile(r"^[A-Z]{1,3}$")


def _event_calendar_dates(event: Event) -> tuple[date, date]:
    """Inclusive UTC calendar bounds for event.start / event.end."""
    start = event.start.astimezone(UTC).date()
    end = event.end.astimezone(UTC).date()
    return start, end


def event_printer_candidates(db: Session, event: Event) -> list[Appliance]:
    """Printers with open lendings overlapping the event window (current or planned)."""
    event_start, event_end = _event_calendar_dates(event)
    rows = (
        db.query(Appliance)
        .join(ApplianceLending, ApplianceLending.appliance_id == Appliance.id)
        .filter(
            Appliance.type == "printer",
            ApplianceLending.organisation_id == event.organisation_id,
            ApplianceLending.returned_at.is_(None),
            ApplianceLending.start_date <= event_end,
            ApplianceLending.end_date >= event_start,
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
        raise api_error("printer_not_available_via_lending", status.HTTP_422_UNPROCESSABLE_CONTENT)


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
        raise api_error("articles_not_in_organisation", status.HTTP_422_UNPROCESSABLE_CONTENT)
    rows = db.query(Article.id, Article.is_addition).filter(Article.id.in_(list(set(article_ids)))).all()
    for aid, is_addition in rows:
        if is_addition:
            raise api_error("zusatz_cannot_assign_station", status.HTTP_422_UNPROCESSABLE_CONTENT, article_id=aid)


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
                    raise api_error("validation_failed", status.HTTP_422_UNPROCESSABLE_CONTENT)


def assert_source_waiter_in_org(db: Session, event: Event, source_waiter_id: int | None) -> None:
    if source_waiter_id is None:
        return
    w = db.query(Waiter).filter(Waiter.id == source_waiter_id).first()
    if not w or w.organisation_id != event.organisation_id:
        raise api_error("source_waiter_wrong_organisation", status.HTTP_422_UNPROCESSABLE_CONTENT)


def assert_exactly_one_default_layout(layouts_payload: list) -> None:
    defaults = [lo for lo in layouts_payload if lo.is_default]
    if len(defaults) != 1:
        raise api_error("exactly_one_default_layout", status.HTTP_422_UNPROCESSABLE_CONTENT)


def assert_cash_registers_valid(db: Session, event: Event, registers_payload: list, layouts_payload: list) -> None:
    layout_uuids = {
        str(getattr(lo, "uuid", "") or "").strip()
        for lo in layouts_payload
        if str(getattr(lo, "uuid", "") or "").strip()
    }
    for reg in registers_payload:
        prefix = str(getattr(reg, "pickup_code_prefix", "") or "").strip().upper()
        if not PICKUP_PREFIX_RE.match(prefix):
            raise api_error("pickup_prefix_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT)
        layout_uuid = str(getattr(reg, "layout_uuid", "") or "").strip()
        if layout_uuid not in layout_uuids:
            raise api_error("cash_register_layout_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT)
        assert_printer_eligible(db, event, getattr(reg, "receipt_printer_appliance_id", None))
        drawer_cmd = str(getattr(reg, "cash_drawer_command", None) or "none").strip().lower()
        if drawer_cmd not in ("", "none") and not getattr(reg, "receipt_printer_appliance_id", None):
            raise api_error("cash_drawer_requires_receipt_printer", status.HTTP_422_UNPROCESSABLE_CONTENT)


def assert_layout_cells_within_grid(layouts_payload: list) -> None:
    for layout in layouts_payload:
        w, h = layout.grid_width, layout.grid_height
        seen: set[tuple[int, int]] = set()
        for cell in layout.cells:
            if not (0 <= cell.row < h and 0 <= cell.col < w):
                raise api_error("cell_out_of_bounds", status.HTTP_422_UNPROCESSABLE_CONTENT, row=cell.row, col=cell.col, width=w, height=h)
            key = (cell.row, cell.col)
            if key in seen:
                raise api_error("duplicate_cell_position", status.HTTP_422_UNPROCESSABLE_CONTENT, row=cell.row, col=cell.col)
            seen.add(key)


def station_printer_appliance_ids(stations_payload: list) -> set[int]:
    out: set[int] = set()
    for st in stations_payload:
        pid = getattr(st, "printer_appliance_id", None)
        if pid is not None:
            out.add(int(pid))
        for rule in getattr(st, "printer_rules", None) or []:
            rpid = getattr(rule, "printer_appliance_id", None)
            if rpid is not None:
                out.add(int(rpid))
    return out


def assert_station_printer_rules_valid(db: Session, event: Event, stations_payload: list) -> None:
    if not bool(getattr(event, "alternative_printers_enabled", False)):
        for st in stations_payload:
            if getattr(st, "printer_rules", None):
                raise api_error("alternative_printers_required", status.HTTP_422_UNPROCESSABLE_CONTENT)
        return

    for st in stations_payload:
        ranges: list[tuple[int, int]] = []
        prefixes: set[str] = set()
        rules = sorted(getattr(st, "printer_rules", None) or [], key=lambda r: int(getattr(r, "sort_order", 0) or 0))
        for idx, rule in enumerate(rules):
            rtype = str(getattr(rule, "rule_type", "") or "").strip()
            pid = getattr(rule, "printer_appliance_id", None)
            assert_printer_eligible(db, event, pid)
            if rtype == "table_range":
                t_from = getattr(rule, "table_from", None)
                t_to = getattr(rule, "table_to", None)
                if t_from is None or t_to is None:
                    raise api_error("table_range_fields_required", status.HTTP_422_UNPROCESSABLE_CONTENT)
                t_from_i, t_to_i = int(t_from), int(t_to)
                if not (1 <= t_from_i <= 99999 and 1 <= t_to_i <= 99999 and t_from_i <= t_to_i):
                    raise api_error("table_range_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT)
                for existing_from, existing_to in ranges:
                    if not (t_to_i < existing_from or t_from_i > existing_to):
                        raise api_error("table_ranges_overlap", status.HTTP_422_UNPROCESSABLE_CONTENT)
                ranges.append((t_from_i, t_to_i))
            elif rtype == "pickup_prefix":
                prefix = str(getattr(rule, "pickup_prefix", "") or "").strip().upper()
                if not PICKUP_PREFIX_RE.match(prefix):
                    raise api_error("pickup_prefix_rule_invalid", status.HTTP_422_UNPROCESSABLE_CONTENT)
                if prefix in prefixes:
                    raise api_error("duplicate_pickup_prefix", status.HTTP_422_UNPROCESSABLE_CONTENT)
                prefixes.add(prefix)
            else:
                raise api_error("unknown_printer_rule_type", status.HTTP_422_UNPROCESSABLE_CONTENT, rule_type=rtype)


def assert_kitchen_monitors_valid(
    db: Session,
    event: Event,
    kitchen_monitors_payload: list,
    stations_payload: list,
    cash_registers_payload: list,
) -> None:
    if not bool(getattr(event, "kitchen_monitors_enabled", False)):
        if kitchen_monitors_payload:
            raise api_error("kitchen_monitors_required", status.HTTP_422_UNPROCESSABLE_CONTENT)
        return
    allowed = station_printer_appliance_ids(stations_payload)
    for reg in cash_registers_payload:
        rpid = getattr(reg, "receipt_printer_appliance_id", None)
        if rpid is not None:
            allowed.add(int(rpid))
    seen: set[int] = set()
    for idx, row in enumerate(kitchen_monitors_payload):
        pid = getattr(row, "printer_appliance_id", None)
        if pid is None:
            raise api_error("kitchen_monitor_printer_required", status.HTTP_422_UNPROCESSABLE_CONTENT)
        pid_int = int(pid)
        if pid_int in seen:
            raise api_error("duplicate_kitchen_monitor_printer", status.HTTP_422_UNPROCESSABLE_CONTENT)
        seen.add(pid_int)
        assert_printer_eligible(db, event, pid_int)
        if allowed and pid_int not in allowed:
            raise api_error("kitchen_monitor_printer_unassigned", status.HTTP_422_UNPROCESSABLE_CONTENT)


def replace_event_configuration(
    db: Session,
    event: Event,
    *,
    stations_in: list,
    event_waiters_in: list,
    app_layouts_in: list,
    cash_registers_in: list | None = None,
    voucher_definitions_in: list | None = None,
    kitchen_monitors_in: list | None = None,
) -> None:
    """Replace all configuration children. Caller must commit. Validates before mutating."""
    cash_registers_in = cash_registers_in or []
    voucher_definitions_in = voucher_definitions_in or []
    kitchen_monitors_in = kitchen_monitors_in or []
    for st in stations_in:
        assert_station_articles_in_org(db, event, list(st.article_ids))
        assert_printer_eligible(db, event, st.printer_appliance_id)
    assert_station_printer_rules_valid(db, event, stations_in)
    assert_kitchen_monitors_valid(db, event, kitchen_monitors_in, stations_in, cash_registers_in)
    for ew in event_waiters_in:
        assert_source_waiter_in_org(db, event, ew.source_waiter_id)

    assert_exactly_one_default_layout(app_layouts_in)
    assert_layout_cells_within_grid(app_layouts_in)
    assert_layout_cells_vouchers(db, event, app_layouts_in, voucher_definitions_in)
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
                kitchen_monitor_enabled=False,
            )
            db.add(st)
            db.flush()
        else:
            st.name = st_in.name.strip()
            st.sort_order = idx
            st.printer_appliance_id = st_in.printer_appliance_id
            st.kitchen_monitor_enabled = False
        kept_station_uuids.add(st.uuid)
        if st_in.article_ids:
            arts = db.query(Article).filter(Article.id.in_(list(set(st_in.article_ids)))).all()
            st.articles = arts
        else:
            st.articles = []
        db.query(EventStationPrinterRule).filter(EventStationPrinterRule.station_id == st.id).delete()
        db.flush()
        if bool(getattr(event, "alternative_printers_enabled", False)):
            for rule_idx, rule_in in enumerate(getattr(st_in, "printer_rules", None) or []):
                db.add(
                    EventStationPrinterRule(
                        station_id=st.id,
                        sort_order=rule_idx,
                        rule_type=str(getattr(rule_in, "rule_type", "") or "").strip(),
                        table_from=getattr(rule_in, "table_from", None),
                        table_to=getattr(rule_in, "table_to", None),
                        pickup_prefix=(
                            str(getattr(rule_in, "pickup_prefix", "") or "").strip().upper() or None
                        ),
                        printer_appliance_id=getattr(rule_in, "printer_appliance_id", None),
                    )
                )

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
                subsidiary_code=(getattr(ew_in, "subsidiary_code", None) or "").strip() or None,
            )
            db.add(ew)
        else:
            ew.name = ew_in.name.strip()
            ew.pin = str(ew_in.pin)
            ew.source_waiter_id = ew_in.source_waiter_id
            ew.subsidiary_code = (getattr(ew_in, "subsidiary_code", None) or "").strip() or None
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
            v_uuids = normalize_cell_voucher_uuids(c)
            v_uuid = v_uuids[0] if v_uuids else None
            cell = EventAppLayoutCell(
                layout_id=lo.id,
                row=c.row,
                col=c.col,
                label=(c.label or "").strip(),
                color=(c.color or "#eeeeee").strip() or "#eeeeee",
                voucher_definition_uuid=v_uuid,
                voucher_definition_uuids=v_uuids,
            )
            db.add(cell)
            db.flush()
            if c.article_ids:
                arts = db.query(Article).filter(Article.id.in_(list(set(c.article_ids)))).all()
                cell.articles = arts

    replace_event_voucher_definitions(db, event, voucher_definitions_in)

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
        reg.cash_drawer_command = str(getattr(reg_in, "cash_drawer_command", None) or "none").strip().lower() or "none"
        reg.subsidiary_code = (getattr(reg_in, "subsidiary_code", None) or "").strip() or None
        kept_register_uuids.add(reg.uuid)

    for reg_uuid, reg in list(existing_registers.items()):
        if reg_uuid not in kept_register_uuids:
            db.delete(reg)

    db.query(EventKitchenMonitorPrinter).filter(EventKitchenMonitorPrinter.event_id == event.id).delete()
    db.flush()
    if bool(getattr(event, "kitchen_monitors_enabled", False)):
        for idx, row_in in enumerate(kitchen_monitors_in):
            db.add(
                EventKitchenMonitorPrinter(
                    event_id=event.id,
                    printer_appliance_id=int(row_in.printer_appliance_id),
                    sort_order=idx,
                    label=(str(getattr(row_in, "label", "") or "").strip() or None),
                )
            )


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
