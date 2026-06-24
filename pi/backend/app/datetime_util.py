"""Datetime helpers for API serialization."""

from datetime import datetime, timezone


def utc_iso(dt: datetime | None) -> str | None:
    """Serialize a datetime as UTC ISO 8601 with explicit offset."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()
