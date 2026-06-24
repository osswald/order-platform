"""HTTP error mapping for cloud proxy routes."""

from __future__ import annotations

import httpx
from fastapi import HTTPException

from ..cloud_client import CloudConfigError


def cloud_config_http_error(e: CloudConfigError) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "message": "Pi backend is not configured for cloud sync. Set variables in pi/.env and restart the container.",
            "missing": e.missing,
        },
    )


def cloud_gateway_http_error(e: httpx.HTTPStatusError) -> HTTPException:
    try:
        detail = e.response.json()
    except Exception:
        detail = e.response.text or "Cloud request failed"
    return HTTPException(status_code=e.response.status_code, detail=detail)
