"""Runtime environment helpers."""

import os

_PRODUCTION_ENVS = frozenset({"production", "prod"})


def app_env() -> str:
    return os.getenv("APP_ENV", "development").strip().lower()


def is_production() -> bool:
    return app_env() in _PRODUCTION_ENVS
