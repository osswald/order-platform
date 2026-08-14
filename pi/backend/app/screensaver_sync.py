"""Sync organisation screensaver images from cloud onto the Pi."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .cloud_client import CloudConfigError, CloudRequestError, fetch_screensaver_image
from .screensaver_store import (
    gc_screensaver_store,
    has_screensaver_file,
    manifest_shas,
    store_screensaver_bytes,
)

log = logging.getLogger("vendiqo.pi.screensaver")


async def sync_screensaver_images(
    bundle: dict[str, Any] | None,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Download missing hashes once; GC files not in the current manifest."""
    items = manifest_shas(bundle)
    keep = {row["sha256"] for row in items}
    deleted = gc_screensaver_store(keep)
    downloaded: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, str]] = []

    for row in items:
        sha = row["sha256"]
        if has_screensaver_file(sha):
            skipped.append(sha)
            continue
        try:
            _mime, raw = await fetch_screensaver_image(sha, client=client)
            store_screensaver_bytes(sha, raw)
            downloaded.append(sha)
        except (CloudConfigError, CloudRequestError, ValueError, OSError) as exc:
            log.warning("screensaver download failed for %s: %s", sha, exc)
            errors.append({"sha256": sha, "error": str(exc)})

    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "deleted": deleted,
        "errors": errors,
    }
