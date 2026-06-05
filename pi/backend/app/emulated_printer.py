"""Store ESC/POS payloads as emulated receipts instead of sending to a printer."""

from __future__ import annotations

import base64
import os
import re
from typing import Any

from sqlalchemy.orm import Session

from .models import EmulatedReceipt

# ESC sequences with a single parameter byte (total 3 bytes).
_ESC_ONE_PARAM = frozenset(
    {
        0x21,  # select print mode
        0x45,  # bold
        0x61,  # justification
        0x74,  # code page
        0x4D,  # font
        0x2D,  # underline
        0x64,  # feed n lines
    }
)

_ALIGN_MAP = {0: "left", 1: "center", 2: "right"}


def _default_style_state() -> dict[str, Any]:
    return {
        "align": "left",
        "font_b": False,
        "bold": False,
        "double_height": False,
        "double_width": False,
        "gs_scale_w": 1,
        "gs_scale_h": 1,
    }


def _style_from_state(state: dict[str, Any]) -> dict[str, Any]:
    scale = max(int(state["gs_scale_w"]), int(state["gs_scale_h"]))
    if scale > 1:
        size = "xlarge"
        scale_val: int | None = scale
    elif state["double_height"] and state["double_width"]:
        size = "large"
        scale_val = None
    elif state["font_b"]:
        size = "small"
        scale_val = None
    else:
        size = "normal"
        scale_val = None
    return {
        "align": state["align"],
        "size": size,
        "scale": scale_val,
        "bold": bool(state["bold"]),
        "kind": "text",
    }


def _reset_style_state(state: dict[str, Any]) -> None:
    state.update(_default_style_state())


def _apply_esc_command(state: dict[str, Any], cmd: int, param: int | None) -> None:
    if cmd == 0x40:
        _reset_style_state(state)
        return
    if param is None:
        return
    if cmd == 0x61:
        state["align"] = _ALIGN_MAP.get(param, "left")
    elif cmd == 0x21:
        state["font_b"] = bool(param & 0x01)
        state["bold"] = bool(param & 0x08)
        state["double_height"] = bool(param & 0x10)
        state["double_width"] = bool(param & 0x20)
    elif cmd == 0x4D:
        state["font_b"] = param == 1
    elif cmd == 0x45:
        state["bold"] = param in (1, 0xFF)


def _apply_gs_char_size(state: dict[str, Any], param: int) -> None:
    if param == 0:
        state["gs_scale_w"] = 1
        state["gs_scale_h"] = 1
        return
    state["gs_scale_w"] = (param & 0x0F) + 1
    state["gs_scale_h"] = ((param >> 4) & 0x0F) + 1


def _is_logo_command(data: bytes, i: int) -> bool:
    if i + 2 >= len(data) or data[i] != 0x1D:
        return False
    cmd = data[i + 1]
    if cmd == 0x28 and data[i + 2] == 0x4B:
        return True
    if cmd == 0x76 and i + 2 < len(data) and data[i + 2] == 0x30:
        return True
    return False


def _escpos_skip_length(data: bytes, i: int) -> int:
    """Return number of bytes to skip starting at ESC (0x1B) or GS (0x1D)."""
    if i >= len(data):
        return 0
    prefix = data[i]
    if prefix not in (0x1B, 0x1D) or i + 1 >= len(data):
        return 1

    cmd = data[i + 1]

    if prefix == 0x1B:
        if cmd == 0x40:
            return 2
        if cmd in _ESC_ONE_PARAM:
            return 3 if i + 2 < len(data) else 2
        return 2

    if cmd == 0x21:
        return 3 if i + 2 < len(data) else 2
    if cmd == 0x56:
        return 4 if i + 3 < len(data) else min(3, len(data) - i)
    if cmd == 0x28 and i + 2 < len(data) and data[i + 2] == 0x4B:
        if i + 4 < len(data):
            payload_len = data[i + 3] + (data[i + 4] << 8)
            return min(5 + payload_len, len(data) - i)
        return 3
    if cmd == 0x76 and i + 2 < len(data) and data[i + 2] == 0x30:
        if i + 6 < len(data):
            width = data[i + 4] + (data[i + 5] << 8)
            height = data[i + 6] + (data[i + 7] << 8) if i + 7 < len(data) else 0
            raster_bytes = ((width + 7) // 8) * height
            return min(8 + raster_bytes, len(data) - i)
        return 3

    return 2


def _decode_text_chunk(raw: bytes) -> str:
    try:
        return raw.decode("cp858", errors="replace")
    except Exception:
        return raw.decode("latin-1", errors="replace")


def _flush_line(buffer: bytearray, state: dict[str, Any], lines: list[dict[str, Any]]) -> None:
    if not buffer:
        return
    text = _decode_text_chunk(bytes(buffer)).rstrip("\r")
    buffer.clear()
    if not text and not lines:
        return
    props = _style_from_state(state)
    props["text"] = text
    lines.append(props)


def _append_logo_line(lines: list[dict[str, Any]]) -> None:
    if lines and lines[-1].get("kind") == "logo":
        return
    lines.append(
        {
            "text": "",
            "align": "center",
            "size": "normal",
            "scale": None,
            "bold": False,
            "kind": "logo",
        }
    )


def escpos_bytes_to_preview_lines(data: bytes) -> list[dict[str, Any]]:
    """Parse ESC/POS bytes into styled preview lines for UI rendering."""
    state = _default_style_state()
    lines: list[dict[str, Any]] = []
    buffer = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b in (0x1B, 0x1D):
            if _is_logo_command(data, i):
                _flush_line(buffer, state, lines)
                _append_logo_line(lines)
                i += _escpos_skip_length(data, i)
                continue
            if b == 0x1B and i + 1 < len(data):
                cmd = data[i + 1]
                param = data[i + 2] if i + 2 < len(data) and cmd in _ESC_ONE_PARAM else None
                _apply_esc_command(state, cmd, param)
            elif b == 0x1D and i + 1 < len(data) and data[i + 1] == 0x21:
                param = data[i + 2] if i + 2 < len(data) else 0
                _apply_gs_char_size(state, param)
            i += _escpos_skip_length(data, i)
            continue
        if b == 0x0A:
            _flush_line(buffer, state, lines)
            i += 1
            continue
        if b == 0x0D:
            i += 1
            continue
        if b >= 0x20:
            buffer.append(b)
        i += 1
    _flush_line(buffer, state, lines)
    return lines


def escpos_bytes_to_preview(data: bytes) -> str:
    """Best-effort text extraction from ESC/POS bytes for UI preview."""
    text = "\n".join(
        line["text"] for line in escpos_bytes_to_preview_lines(data) if line.get("kind") != "logo"
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_emulated_printer_mode() -> bool:
    return os.getenv("PRINTER_MODE", "").strip().lower() == "emulated"


def store_emulated_receipt(
    db: Session,
    *,
    data: bytes,
    job_kind: str | None = None,
    station_name: str | None = None,
) -> EmulatedReceipt:
    row = EmulatedReceipt(
        job_kind=job_kind,
        station_name=station_name,
        escpos_payload=base64.b64encode(data).decode("ascii"),
        preview_text=escpos_bytes_to_preview(data),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
