import os


DEFAULT_CLOUD_BASE_URL = os.environ.get("DEFAULT_CLOUD_BASE_URL", "https://api.vendiqo.ch").strip().rstrip("/")


def resolve_cloud_base_url() -> str:
    url = DEFAULT_CLOUD_BASE_URL
    if not url.startswith(("http://", "https://")):
        raise ValueError("Cloud URL must start with http:// or https://")
    return url
