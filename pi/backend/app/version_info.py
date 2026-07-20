"""Runtime version metadata baked into Docker images at build time."""

from __future__ import annotations

import os


def get_app_version() -> str:
    value = os.getenv("APP_VERSION", "0.0.0-dev").strip()
    return value or "0.0.0-dev"


def get_build_time() -> str | None:
    value = os.getenv("APP_BUILD_TIME", "").strip()
    return value or None
