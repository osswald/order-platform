"""Unit tests for Umsatz name resolution (UUID + legacy int)."""

from app.event_sales import (
    _is_generic_station_label,
    _line_station_uuid,
    _payload_waiter_uuid,
    _resolve_station_name,
    _resolve_waiter_name,
    _upgrade_bucket_name,
)


def _maps(
    *,
    station_by_uuid=None,
    station_by_int=None,
    waiter_by_uuid=None,
    waiter_by_int=None,
):
    return {
        "station_names_by_uuid": station_by_uuid or {},
        "article_station_uuid": {},
        "station_names_by_int": station_by_int or {},
        "waiter_by_uuid": waiter_by_uuid or {},
        "waiter_by_int": waiter_by_int or {},
        "waiter_by_source": {},
        "global_waiter": {},
    }


def test_resolve_station_name_by_uuid():
    maps = _maps(station_by_uuid={"abc-uuid": "Bar"})
    assert _resolve_station_name({}, "abc-uuid", None, maps) == "Bar"


def test_resolve_station_name_legacy_int():
    maps = _maps(station_by_int={32: "Haupttresen"})
    assert _resolve_station_name({}, None, 32, maps) == "Haupttresen"


def test_resolve_station_name_unknown_uuid_fallback():
    maps = _maps()
    label = _resolve_station_name({}, "12345678-abcd-efgh-ijkl-123456789012", None, maps)
    assert label.startswith("Station ")


def test_resolve_waiter_name_by_uuid():
    maps = _maps(waiter_by_uuid={"w-uuid": "Anna"})
    payload = {"waiter_uuid": "w-uuid"}
    assert _resolve_waiter_name(payload, "w-uuid", None, maps) == "Anna"


def test_resolve_waiter_name_legacy_int():
    maps = _maps(waiter_by_int={5: "Bob"})
    assert _resolve_waiter_name({}, None, 5, maps) == "Bob"


def test_payload_waiter_uuid_helper():
    assert _payload_waiter_uuid({"waiter_uuid": "  x  "}) == "x"
    assert _payload_waiter_uuid({}) is None


def test_line_station_uuid_helper():
    assert _line_station_uuid({"station_uuid": "s1"}) == "s1"


def test_upgrade_bucket_name_replaces_generic():
    assert (
        _upgrade_bucket_name("Station #32", "Bar", _is_generic_station_label)
        == "Bar"
    )
