"""Response model for GET /v1/bundle (synced organisation payload)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EdgeBundleResponse(BaseModel):
    """Organisation bundle pulled from cloud; event/article shape varies by sync."""

    model_config = ConfigDict(extra="allow")

    organisation_id: int
    events: list[dict[str, Any]] = Field(default_factory=list)
