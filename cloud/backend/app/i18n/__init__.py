"""Lightweight JSON-based i18n for cloud backend."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEFAULT_LOCALE = "de"
SUPPORTED_LOCALES = frozenset({"de", "en"})
_LOCALES_DIR = Path(__file__).resolve().parent / "locales"


@lru_cache(maxsize=len(SUPPORTED_LOCALES))
def _load_locale(locale: str) -> dict:
    path = _LOCALES_DIR / f"{locale}.json"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _lookup(messages: dict, key: str) -> str | None:
    node: object = messages
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def normalize_locale(value: str | None) -> str:
    if not value:
        return DEFAULT_LOCALE
    primary = value.split(",")[0].strip().split(";")[0].strip().lower()
    if primary.startswith("de"):
        return "de"
    if primary.startswith("en"):
        return "en"
    return DEFAULT_LOCALE


def resolve_locale_from_accept_language(header: str | None) -> str:
    if not header:
        return DEFAULT_LOCALE
    for part in header.split(","):
        token = part.strip().split(";")[0].strip().lower()
        if not token:
            continue
        if token.startswith("de"):
            return "de"
        if token.startswith("en"):
            return "en"
    return DEFAULT_LOCALE


def t(key: str, locale: str = DEFAULT_LOCALE, **params: object) -> str:
    loc = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    text = _lookup(_load_locale(loc), key)
    if text is None and loc != DEFAULT_LOCALE:
        text = _lookup(_load_locale(DEFAULT_LOCALE), key)
    if text is None:
        return key
    if params:
        return text.format(**params)
    return text
