"""Per-printer appliance ESC/POS options (synced to Pi via edge bundle)."""

from pydantic import BaseModel, Field


class PrinterHostEndpoint(BaseModel):
    host: str
    port: int = Field(default=9100, ge=1, le=65535)
    feed_lines: int = Field(default=1, ge=0, le=10)


def feed_lines_for_appliance(appliance) -> int:
    raw = getattr(appliance, "escpos_feed_lines", None)
    if raw is None:
        return 1
    return max(0, min(10, int(raw)))
