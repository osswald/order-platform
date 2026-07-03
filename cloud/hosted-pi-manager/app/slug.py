"""Validation helpers for hosted Pi instance slugs."""

from __future__ import annotations

import re
from pathlib import Path

HOSTED_PI_SLUG_RE = re.compile(r"^[a-f0-9]{12}$")


def validate_slug(slug: str) -> str:
    if not HOSTED_PI_SLUG_RE.fullmatch(slug):
        raise ValueError("invalid hosted Pi slug")
    return slug


def safe_path_under(root: Path, *parts: str) -> Path:
    candidate = root.joinpath(*parts).resolve()
    root_resolved = root.resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ValueError("path escapes hosted Pi root directory")
    return candidate
