"""Conditional printer routing and per-printer kitchen monitor helpers."""

from __future__ import annotations

from .printer_endpoint import parse_printer_host_entry, resolve_printer_endpoint


def appliance_host_key(appliance_id: int) -> str:
    return f"appliance:{appliance_id}"


def _station_config(ev: dict, station_uuid: str | None) -> dict | None:
    if station_uuid is None:
        return None
    for st in (ev.get("configuration") or {}).get("stations") or []:
        if str(st.get("uuid")) == str(station_uuid):
            return st
    return None


def _pickup_prefix(pickup_code: str | None) -> str:
    if not pickup_code:
        return ""
    code = str(pickup_code).strip().upper()
    prefix = ""
    for ch in code:
        if ch.isalpha():
            prefix += ch
        else:
            break
    return prefix


def resolve_printer_appliance_id(
    ev: dict,
    station_uuid: str | None,
    *,
    table_number: int | None = None,
    pickup_code: str | None = None,
) -> int | None:
    st = _station_config(ev, station_uuid)
    if not st:
        return None
    default_id = st.get("printer_appliance_id")
    if not bool(ev.get("alternative_printers_enabled")):
        return int(default_id) if default_id is not None else None

    rules = sorted(st.get("printer_rules") or [], key=lambda r: int(r.get("sort_order") or 0))
    table_n = int(table_number or 0)
    prefix = _pickup_prefix(pickup_code)
    for rule in rules:
        rtype = str(rule.get("rule_type") or "")
        if rtype == "table_range":
            t_from = rule.get("table_from")
            t_to = rule.get("table_to")
            if t_from is None or t_to is None:
                continue
            if table_n > 0 and int(t_from) <= table_n <= int(t_to):
                pid = rule.get("printer_appliance_id")
                return int(pid) if pid is not None else None
        elif rtype == "pickup_prefix":
            rp = str(rule.get("pickup_prefix") or "").strip().upper()
            if rp and prefix == rp:
                pid = rule.get("printer_appliance_id")
                return int(pid) if pid is not None else None
    return int(default_id) if default_id is not None else None


def resolve_printer_target(
    ev: dict,
    station_uuid: str | None,
    *,
    table_number: int | None = None,
    pickup_code: str | None = None,
) -> tuple[str, int, int, int | None]:
    appliance_id = resolve_printer_appliance_id(
        ev,
        station_uuid,
        table_number=table_number,
        pickup_code=pickup_code,
    )
    hosts = ev.get("printer_hosts") or {}
    raw = None
    if appliance_id is not None:
        raw = hosts.get(appliance_host_key(int(appliance_id)))
    if raw is None and station_uuid and str(station_uuid) in hosts:
        raw = hosts[str(station_uuid)]
    entry = parse_printer_host_entry(raw) if raw is not None else None
    if entry and entry["host"]:
        return entry["host"], int(entry["port"]), int(entry["feed_lines"]), appliance_id
    host, port, feed = resolve_printer_endpoint(ev, station_uuid)
    return host, port, feed, appliance_id


def resolve_endpoint_by_appliance(ev: dict, appliance_id: int | None) -> tuple[str, int, int]:
    if appliance_id is None:
        return resolve_printer_endpoint(ev, None)
    hosts = ev.get("printer_hosts") or {}
    key = appliance_host_key(int(appliance_id))
    raw = hosts.get(key)
    entry = parse_printer_host_entry(raw) if raw is not None else None
    if entry and entry["host"]:
        return entry["host"], int(entry["port"]), int(entry["feed_lines"])
    return resolve_printer_endpoint(ev, None)


def subgroup_lines_by_printer(
    ev: dict,
    station_uuid: str | None,
    lines: list[dict],
    order_ctx: dict,
) -> dict[int | None, list[dict]]:
    groups: dict[int | None, list[dict]] = {}
    table_number = order_ctx.get("table_number")
    pickup_code = order_ctx.get("pickup_code")
    for line in lines:
        if not isinstance(line, dict):
            continue
        pid = resolve_printer_appliance_id(
            ev,
            station_uuid,
            table_number=table_number,
            pickup_code=pickup_code,
        )
        groups.setdefault(pid, []).append(dict(line))
    if not groups:
        groups[None] = []
    return groups


def kitchen_monitors_for_event(ev: dict) -> list[dict]:
    cfg = (ev.get("configuration") or {}).get("kitchen_monitors") or []
    if cfg:
        return sorted(cfg, key=lambda m: (int(m.get("sort_order") or 0), str(m.get("label") or "")))
    out: list[dict] = []
    seen: set[int] = set()
    for st in (ev.get("configuration") or {}).get("stations") or []:
        if not st.get("kitchen_monitor_enabled"):
            continue
        pid = st.get("printer_appliance_id")
        if pid is None:
            continue
        pid_int = int(pid)
        if pid_int in seen:
            continue
        seen.add(pid_int)
        out.append(
            {
                "printer_appliance_id": pid_int,
                "label": st.get("name") or f"Drucker #{pid_int}",
                "sort_order": len(out),
            }
        )
    return out


def kitchen_monitors_enabled(ev: dict) -> bool:
    if bool(ev.get("kitchen_monitors_enabled")):
        return True
    return bool(kitchen_monitors_for_event(ev))


def printer_in_kitchen_monitor(ev: dict, printer_appliance_id: int | None) -> bool:
    if not kitchen_monitors_enabled(ev):
        return False
    if printer_appliance_id is None:
        return False
    monitors = kitchen_monitors_for_event(ev)
    if not monitors:
        return False
    target = int(printer_appliance_id)
    return target in {int(m["printer_appliance_id"]) for m in monitors if m.get("printer_appliance_id") is not None}


def kitchen_monitor_label(ev: dict, printer_appliance_id: int | None) -> str:
    if printer_appliance_id is None:
        return "Drucker"
    target = int(printer_appliance_id)
    for row in kitchen_monitors_for_event(ev):
        if int(row.get("printer_appliance_id") or 0) == target:
            label = str(row.get("label") or "").strip()
            if label:
                return label
    return f"Drucker #{target}"
