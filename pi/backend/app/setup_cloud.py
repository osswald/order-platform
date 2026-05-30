"""Cloud URL resolution for Pi setup pairing."""

import os


DEFAULT_CLOUD_BASE_URL = os.environ.get("DEFAULT_CLOUD_BASE_URL", "https://api.vendiqo.ch").strip().rstrip("/")


def allow_cloud_url_override() -> bool:
    return os.getenv("ALLOW_CLOUD_URL_OVERRIDE", "").strip().lower() in ("1", "true", "yes")


def resolve_cloud_base_url(requested: str | None) -> str:
    if allow_cloud_url_override():
        url = (requested or DEFAULT_CLOUD_BASE_URL).strip().rstrip("/")
    else:
        url = DEFAULT_CLOUD_BASE_URL
    if not url.startswith(("http://", "https://")):
        raise ValueError("Cloud URL must start with http:// or https://")
    return url
