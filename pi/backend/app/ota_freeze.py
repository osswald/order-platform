"""OTA freeze signal: host-readable flag when any synced event is prod."""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

FREEZE_FILENAME = "freeze"
DEFAULT_OTA_STATE_DIR = "/ota-state"


def ota_state_dir() -> Path:
    return Path(os.getenv("OTA_STATE_DIR", DEFAULT_OTA_STATE_DIR))


def bundle_requires_ota_freeze(bundle: dict | None) -> bool:
    """True when any event in the synced bundle has status prod."""
    if not isinstance(bundle, dict):
        return False
    for ev in bundle.get("events") or []:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("status") or "").strip().lower() == "prod":
            return True
    return False


def write_ota_freeze_from_bundle(bundle: dict | None) -> None:
    """Write or clear the freeze flag under OTA_STATE_DIR for the host OTA script."""
    state_dir = ota_state_dir()
    freeze_path = state_dir / FREEZE_FILENAME
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        if bundle_requires_ota_freeze(bundle):
            freeze_path.write_text("1\n", encoding="utf-8")
            log.info("OTA freeze enabled (synced prod event) at %s", freeze_path)
        else:
            freeze_path.write_text("0\n", encoding="utf-8")
            log.debug("OTA freeze cleared at %s", freeze_path)
    except OSError as exc:
        log.warning("Failed to write OTA freeze state at %s: %s", freeze_path, exc)


def sync_ota_freeze_from_db(db) -> None:
    """Refresh freeze flag from the current SyncedBundle row (startup / after pull)."""
    from .bundle_cache import get_bundle_dict_raw

    write_ota_freeze_from_bundle(get_bundle_dict_raw(db))
