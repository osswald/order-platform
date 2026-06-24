import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
)

LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "10/minute")
REFRESH_RATE_LIMIT = os.getenv("REFRESH_RATE_LIMIT", "30/minute")
EDGE_PAIR_RATE_LIMIT = os.getenv("EDGE_PAIR_RATE_LIMIT", "20/minute")
CHANGE_PASSWORD_RATE_LIMIT = os.getenv("CHANGE_PASSWORD_RATE_LIMIT", "5/minute")
USERS_RATE_LIMIT = os.getenv("USERS_RATE_LIMIT", "30/minute")
EDGE_WRITE_RATE_LIMIT = os.getenv("EDGE_WRITE_RATE_LIMIT", "120/minute")


def edge_client_key(request: Request) -> str:
    client_id = (request.headers.get("X-Edge-Client-Id") or "").strip()
    if client_id:
        return f"edge:{client_id}"
    return get_remote_address(request)
