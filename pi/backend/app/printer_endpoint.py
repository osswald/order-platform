"""Resolve ESC/POS printer endpoints from synced cloud event bundles."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_FEED_LINES = 1
DEFAULT_PORT = 9100


def parse_printer_host_entry(raw: Any) -> dict[str, Any]:
    """Accept legacy host:port strings or {host, port, feed_lines} objects."""
    if isinstance(raw, dict):
        host = str(raw.get("host") or "").strip()
        try:
            port = int(raw.get("port") or DEFAULT_PORT)
        except (TypeError, ValueError):
            port = DEFAULT_PORT
        feed_raw = raw.get("feed_lines")
        if feed_raw is None:
            feed_lines = DEFAULT_FEED_LINES
        else:
            try:
                feed_lines = max(0, min(10, int(feed_raw)))
            except (TypeError, ValueError):
                feed_lines = DEFAULT_FEED_LINES
        return {"host": host, "port": port, "feed_lines": feed_lines}
    if isinstance(raw, str):
        host, _, port_s = raw.partition(":")
        try:
            port = int(port_s or DEFAULT_PORT)
        except ValueError:
            port = DEFAULT_PORT
        return {"host": host.strip(), "port": port, "feed_lines": DEFAULT_FEED_LINES}
    return {"host": "", "port": DEFAULT_PORT, "feed_lines": DEFAULT_FEED_LINES}


def resolve_printer_endpoint(ev: dict, station_uuid: str | None) -> tuple[str, int, int]:
    hosts = ev.get("printer_hosts") or {}
    key = str(station_uuid) if station_uuid is not None else None
    raw: Any = None
    if key and key in hosts:
        raw = hosts[key]
    elif hosts:
        raw = next(iter(hosts.values()))
    entry = parse_printer_host_entry(raw) if raw is not None else None
    if entry and entry["host"]:
        return entry["host"], int(entry["port"]), int(entry["feed_lines"])
    host = os.getenv("DEFAULT_PRINTER_HOST", "192.168.192.11")
    port = int(os.getenv("DEFAULT_PRINTER_PORT", "9100"))
    return host, port, DEFAULT_FEED_LINES
