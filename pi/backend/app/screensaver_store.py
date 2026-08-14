"""Local content-addressed screensaver image store on the Pi."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
from pathlib import Path

_SHA_RE = re.compile(r"^[a-f0-9]{64}$")
log = logging.getLogger("vendiqo.pi.screensaver_store")


def screensaver_dir() -> Path:
    configured = os.getenv("SCREENSAVER_DIR")
    if configured:
        return Path(configured)
    return Path("/data/screensaver")


def _safe_sha(sha256: str) -> str:
    key = (sha256 or "").strip().lower()
    if not _SHA_RE.match(key):
        raise ValueError("invalid sha256")
    return key


def path_for_sha(sha256: str) -> Path:
    return screensaver_dir() / _safe_sha(sha256)


def has_screensaver_file(sha256: str) -> bool:
    try:
        return path_for_sha(sha256).is_file()
    except ValueError:
        return False


def list_local_shas() -> set[str]:
    root = screensaver_dir()
    if not root.is_dir():
        return set()
    return {p.name for p in root.iterdir() if p.is_file() and _SHA_RE.match(p.name)}


def store_screensaver_bytes(sha256: str, raw: bytes) -> Path:
    key = _safe_sha(sha256)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != key:
        raise ValueError("sha256 mismatch")
    root = screensaver_dir()
    root.mkdir(parents=True, exist_ok=True)
    path = root / key
    tmp = root / f".{key}.tmp"
    tmp.write_bytes(raw)
    tmp.replace(path)
    return path


def delete_screensaver_file(sha256: str) -> bool:
    try:
        path = path_for_sha(sha256)
    except ValueError:
        return False
    if not path.is_file():
        return False
    path.unlink()
    return True


def wipe_screensaver_store() -> None:
    root = screensaver_dir()
    try:
        if root.is_dir():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.warning("Failed to wipe screensaver store at %s: %s", root, exc)


def gc_screensaver_store(keep_shas: set[str]) -> list[str]:
    """Delete local files whose sha is not in keep_shas. Returns deleted shas."""
    keep = {_safe_sha(s) for s in keep_shas if s}
    deleted: list[str] = []
    for sha in list_local_shas():
        if sha not in keep:
            if delete_screensaver_file(sha):
                deleted.append(sha)
    return deleted


def read_screensaver_bytes(sha256: str) -> bytes | None:
    try:
        path = path_for_sha(sha256)
    except ValueError:
        return None
    if not path.is_file():
        return None
    return path.read_bytes()


def manifest_shas(bundle: dict | None) -> list[dict[str, str]]:
    """Return [{sha256, mime}, ...] from bundle screensaver_images."""
    if not isinstance(bundle, dict):
        return []
    rows = bundle.get("screensaver_images") or []
    out: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sha = str(row.get("sha256") or "").strip().lower()
        mime = str(row.get("mime") or "application/octet-stream").strip()
        if _SHA_RE.match(sha):
            out.append({"sha256": sha, "mime": mime})
    return out
