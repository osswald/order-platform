"""CSRF protections for cookie-authenticated admin API requests."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .i18n import t
from .i18n.context import get_request_locale

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
EXEMPT_PATH_PREFIXES = (
    "/health",
    "/edge",
    "/stripe/webhooks",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/token",  # password login; not ambient-cookie CSRF
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]


def _origin_from_referer(referer: str | None) -> str | None:
    if not referer:
        return None
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def request_origin_allowed(request: Request) -> bool:
    origin = request.headers.get("origin")
    if origin and origin in allowed_origins:
        return True
    ref_origin = _origin_from_referer(request.headers.get("referer"))
    return bool(ref_origin and ref_origin in allowed_origins)


def _path_exempt(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in EXEMPT_PATH_PREFIXES)


def _has_bearer(request: Request) -> bool:
    auth = request.headers.get("authorization") or ""
    return auth.lower().startswith("bearer ")


def _has_session_cookie(request: Request) -> bool:
    return bool(request.cookies.get("access_token") or request.cookies.get("refresh_token"))


class CookieCsrfMiddleware(BaseHTTPMiddleware):
    """Require allowlisted Origin/Referer for cookie-authed mutating requests without Bearer."""

    async def dispatch(self, request: Request, call_next):
        if (
            request.method in MUTATING_METHODS
            and not _path_exempt(request.url.path)
            and _has_session_cookie(request)
            and not _has_bearer(request)
            and not request_origin_allowed(request)
        ):
            code = "csrf_origin_rejected"
            message = t(f"errors.{code}", get_request_locale())
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": {"code": code, "message": message}},
            )
        return await call_next(request)
