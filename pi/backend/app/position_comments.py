"""Position comment (line note) validation."""

from __future__ import annotations

from fastapi import HTTPException

MAX_NOTE_LEN = 512


def position_comments_enabled(bundle: dict | None) -> bool:
    return bool((bundle or {}).get("position_comments_enabled"))


def normalize_note(raw) -> str:
    if raw is None:
        return ""
    return str(raw).strip()[:MAX_NOTE_LEN]


def validate_submit_position_notes(bundle: dict, lines: list) -> None:
    """Reject non-empty notes when disabled; normalize notes when enabled."""
    enabled = position_comments_enabled(bundle)
    for line in lines or []:
        if not isinstance(line, dict):
            continue
        note = normalize_note(line.get("note"))
        if note and not enabled:
            raise HTTPException(
                status_code=400,
                detail="Position comments are not enabled for this organisation",
            )
        if enabled:
            line["note"] = note
