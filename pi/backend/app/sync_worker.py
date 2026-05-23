"""Background Pi ↔ cloud sync loop."""

from __future__ import annotations

import asyncio
import logging
import os

from .database import SessionLocal
from .sync_service import run_sync_cycle, sync_status

log = logging.getLogger(__name__)

_cycle_lock = asyncio.Lock()


def _sync_enabled() -> bool:
    return os.getenv("SYNC_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")


def _sync_interval_seconds() -> float:
    try:
        interval = int(os.getenv("SYNC_INTERVAL_SECONDS", "60"))
    except ValueError:
        interval = 60
    return float(max(15, interval))


async def _run_one_cycle() -> None:
    async with _cycle_lock:
        db = SessionLocal()
        try:
            summary = await run_sync_cycle(db)
            if summary.get("skipped"):
                return
            if summary.get("error"):
                log.info(
                    "sync cycle: push_sent=%s pull_ok=%s error=%s",
                    summary.get("push_sent"),
                    summary.get("pull_ok"),
                    summary.get("error"),
                )
            elif summary.get("push_sent") or summary.get("pull_ok"):
                log.debug(
                    "sync cycle ok: push_sent=%s event_count=%s",
                    summary.get("push_sent"),
                    summary.get("event_count"),
                )
        finally:
            db.close()


async def sync_worker_loop(stop_event: asyncio.Event) -> None:
    sync_status["auto_sync_enabled"] = _sync_enabled()
    interval = _sync_interval_seconds()
    log.info("Cloud sync worker started (enabled=%s, interval=%ss)", _sync_enabled(), interval)

    while not stop_event.is_set():
        if _sync_enabled():
            try:
                await _run_one_cycle()
            except Exception as e:
                log.exception("sync worker cycle failed: %s", e)
                sync_status["last_error"] = str(e)[:2000]
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass

    log.info("Cloud sync worker stopped")
