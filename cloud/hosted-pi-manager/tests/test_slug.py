"""Tests for hosted Pi slug validation and safe path resolution."""

from pathlib import Path

import pytest
from app.slug import HOSTED_PI_SLUG_RE, safe_path_under, validate_slug


def test_hosted_pi_slug_pattern_matches_generated_tokens():
    assert HOSTED_PI_SLUG_RE.fullmatch("a1b2c3d4e5f6")
    assert HOSTED_PI_SLUG_RE.fullmatch("0123456789ab")


@pytest.mark.parametrize(
    "slug",
    [
        "../etc",
        "..",
        "/etc/passwd",
        "UPPERCASE12",
        "short",
        "a" * 13,
        "zzzzzzzzzzzz",
        "abc/def",
    ],
)
def test_validate_slug_rejects_unsafe_values(slug: str):
    with pytest.raises(ValueError, match="invalid hosted Pi slug"):
        validate_slug(slug)


def test_safe_path_under_allows_child_directory(tmp_path: Path):
    root = tmp_path / "instances"
    root.mkdir()
    path = safe_path_under(root, "a1b2c3d4e5f6")
    assert path == (root / "a1b2c3d4e5f6").resolve()


def test_safe_path_under_rejects_traversal(tmp_path: Path):
    root = tmp_path / "instances"
    root.mkdir()
    with pytest.raises(ValueError, match="path escapes"):
        safe_path_under(root, "..", "outside")
