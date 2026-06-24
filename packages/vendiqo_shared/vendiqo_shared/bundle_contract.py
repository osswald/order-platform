"""Top-level keys in the edge organisation bundle exchanged between cloud and pi."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

BUNDLE_TOP_LEVEL_KEYS = frozenset(
    {
        "organisation_id",
        "events",
        "position_comments_enabled",
        "position_comment_presets",
        "admin_pin_hashes",
    }
)


class EdgeBundleContract(BaseModel):
    """Minimal validated shape for synced organisation bundles."""

    model_config = ConfigDict(extra="allow")

    organisation_id: int
    events: list[dict[str, Any]] = Field(default_factory=list)
