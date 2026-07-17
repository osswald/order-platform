"""Edge organisation bundle assembly and contract validation."""

from __future__ import annotations

from typing import Any

from vendiqo_shared.bundle_contract import BUNDLE_TOP_LEVEL_KEYS, EdgeBundleContract


def validate_edge_bundle_payload(payload: dict[str, Any]) -> EdgeBundleContract:
    """Validate top-level bundle keys against the shared pi/cloud contract."""
    missing = BUNDLE_TOP_LEVEL_KEYS - set(payload.keys())
    if missing:
        raise ValueError(f"bundle missing required keys: {sorted(missing)}")
    return EdgeBundleContract.model_validate(payload)


def edge_bundle_payload(
    *,
    organisation_id: int,
    events: list[Any],
    admin_pin_hashes: list[str],
    position_comments_enabled: bool,
    position_comment_presets: list[dict[str, Any]],
    ingredients_enabled: bool = False,
) -> dict[str, Any]:
    """Build the organisation bundle dict returned by GET /edge/v1/bundle."""
    payload = {
        "organisation_id": organisation_id,
        "events": events,
        "admin_pin_hashes": admin_pin_hashes,
        "position_comments_enabled": position_comments_enabled,
        "position_comment_presets": position_comment_presets,
        "ingredients_enabled": ingredients_enabled,
    }
    validate_edge_bundle_payload(payload)
    return payload
