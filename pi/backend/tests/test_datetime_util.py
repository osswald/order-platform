"""Tests for datetime_util."""

from datetime import UTC, datetime, timedelta, timezone

from app.datetime_util import utc_iso


def test_utc_iso_none():
    assert utc_iso(None) is None


def test_utc_iso_naive_assumed_utc():
    dt = datetime(2026, 6, 24, 15, 47, 27)
    result = utc_iso(dt)
    assert result is not None
    assert result.endswith("+00:00")
    assert "2026-06-24T15:47:27" in result


def test_utc_iso_aware_utc():
    dt = datetime(2026, 6, 24, 15, 47, 27, tzinfo=UTC)
    assert utc_iso(dt) == "2026-06-24T15:47:27+00:00"


def test_utc_iso_converts_non_utc_offset():
    dt = datetime(2026, 6, 24, 17, 47, 27, tzinfo=timezone(timedelta(hours=2)))
    assert utc_iso(dt) == "2026-06-24T15:47:27+00:00"
