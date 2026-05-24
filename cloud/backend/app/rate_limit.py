import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
)

LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "10/minute")
