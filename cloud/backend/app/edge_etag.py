"""Stable ETag helpers for edge bundle and operational snapshot responses."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize payload to a stable UTF-8 JSON byte string for hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=False,
    ).encode("utf-8")


def etag_for_payload(payload: Any) -> str:
    """Return a strong ETag (quoted hex sha256) for a JSON-serializable payload."""
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f'"{digest}"'


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    """True when If-None-Match includes the given ETag (or is ``*``)."""
    if not if_none_match or not etag:
        return False
    raw = if_none_match.strip()
    if raw == "*":
        return True
    target = etag.strip()
    target_unquoted = target[1:-1] if target.startswith('"') and target.endswith('"') else target
    for part in raw.split(","):
        token = part.strip()
        if token.startswith("W/"):
            token = token[2:].strip()
        if token == target:
            return True
        unquoted = token[1:-1] if token.startswith('"') and token.endswith('"') else token
        if unquoted == target_unquoted:
            return True
    return False
