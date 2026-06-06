"""Conditional printer routing from synced bundle."""

from app.printer_routing import (
    printer_in_kitchen_monitor,
    resolve_printer_appliance_id,
    resolve_printer_target,
    subgroup_lines_by_printer,
)


def _event_bundle() -> dict:
    return {
        "alternative_printers_enabled": True,
        "kitchen_monitors_enabled": True,
        "printer_hosts": {
            "st-1": {"host": "10.0.0.1", "port": 9100, "feed_lines": 1},
            "appliance:20": {"host": "10.0.0.20", "port": 9100, "feed_lines": 2},
            "appliance:21": {"host": "10.0.0.21", "port": 9100, "feed_lines": 0},
        },
        "configuration": {
            "stations": [
                {
                    "uuid": "st-1",
                    "name": "Getränke",
                    "printer_appliance_id": 19,
                    "printer_rules": [
                        {
                            "sort_order": 0,
                            "rule_type": "table_range",
                            "table_from": 1,
                            "table_to": 50,
                            "printer_appliance_id": 20,
                        },
                        {
                            "sort_order": 1,
                            "rule_type": "pickup_prefix",
                            "pickup_prefix": "B",
                            "printer_appliance_id": 21,
                        },
                    ],
                }
            ],
            "kitchen_monitors": [
                {"printer_appliance_id": 20, "label": "Bar West", "sort_order": 0},
            ],
        },
    }


def test_resolve_table_range_rule():
    ev = _event_bundle()
    assert resolve_printer_appliance_id(ev, "st-1", table_number=42) == 20
    assert resolve_printer_appliance_id(ev, "st-1", table_number=99) == 19


def test_resolve_pickup_prefix_rule():
    ev = _event_bundle()
    assert resolve_printer_appliance_id(ev, "st-1", pickup_code="B17") == 21


def test_resolve_printer_target_uses_appliance_host():
    ev = _event_bundle()
    host, port, feed, appliance_id = resolve_printer_target(ev, "st-1", table_number=10)
    assert appliance_id == 20
    assert host == "10.0.0.20"
    assert port == 9100
    assert feed == 2


def test_subgroup_lines_single_printer_when_flag_off():
    ev = _event_bundle()
    ev["alternative_printers_enabled"] = False
    groups = subgroup_lines_by_printer(
        ev,
        "st-1",
        [{"article_id": 1, "qty": 1}],
        {"table_number": 42, "pickup_code": "B1"},
    )
    assert groups == {19: [{"article_id": 1, "qty": 1}]}


def test_printer_in_kitchen_monitor():
    ev = _event_bundle()
    assert printer_in_kitchen_monitor(ev, 20) is True
    assert printer_in_kitchen_monitor(ev, 21) is False
