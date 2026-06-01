"""Printer endpoint resolution from synced bundle."""

from app.printer_endpoint import parse_printer_host_entry, resolve_printer_endpoint


def test_parse_legacy_host_port_string():
    entry = parse_printer_host_entry("192.168.1.20:9100")
    assert entry["host"] == "192.168.1.20"
    assert entry["port"] == 9100
    assert entry["feed_lines"] == 1


def test_parse_object_endpoint():
    entry = parse_printer_host_entry({"host": "10.0.0.5", "port": 9100, "feed_lines": 0})
    assert entry["feed_lines"] == 0


def test_resolve_uses_station_feed_lines():
    ev = {
        "printer_hosts": {
            "st-1": {"host": "192.168.1.30", "port": 9100, "feed_lines": 2},
            "st-2": {"host": "192.168.1.31", "port": 9100, "feed_lines": 0},
        }
    }
    host, port, feed = resolve_printer_endpoint(ev, "st-2")
    assert host == "192.168.1.31"
    assert port == 9100
    assert feed == 0
