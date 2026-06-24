"""Receipt printing defaults, validation, copy, and Pi bundle serialization."""

from __future__ import annotations

import base64
import copy
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

ALLOWED_RECEIPT_LOGO_MIMES = frozenset({"image/png", "image/jpeg", "image/jpg"})
MAX_RECEIPT_LOGO_BYTES = 200 * 1024
MAX_BOTTOM_LINE_CHARS = 500
MAX_LABEL_EVENT_TITLE_CHARS = 120

SizeTableOrPickup = Literal["normal", "large", "xlarge"]
SizeOrderLines = Literal["normal", "large"]


class ReceiptProfileConfig(BaseModel):
    logo_enabled: bool = True
    show_event_title: bool = True
    size_table_or_pickup: SizeTableOrPickup = "large"
    size_order_lines: SizeOrderLines = "normal"
    show_price: bool = False
    bottom_line: str = ""

    @field_validator("bottom_line")
    @classmethod
    def _limit_bottom_line(cls, v: str) -> str:
        return _validate_bottom_line(v)


class PaymentReceiptProfileConfig(BaseModel):
    """Zahlungsbeleg (payment receipt) — compact layout, no hero/pickup sizes."""

    logo_enabled: bool = True
    show_event_title: bool = True
    size_order_lines: SizeOrderLines = "normal"
    bottom_line: str = ""

    @field_validator("bottom_line")
    @classmethod
    def _limit_bottom_line(cls, v: str) -> str:
        return _validate_bottom_line(v)


def _validate_bottom_line(v: str) -> str:
    text = (v or "").replace("\r\n", "\n").replace("\r", "\n")
    if len(text) > MAX_BOTTOM_LINE_CHARS:
        raise ValueError(f"bottom_line max {MAX_BOTTOM_LINE_CHARS} characters")
    lines = text.split("\n")
    if len(lines) > 8:
        raise ValueError("bottom_line max 8 lines")
    return text


def _station_profile_model() -> ReceiptProfileConfig:
    return ReceiptProfileConfig(
        logo_enabled=True,
        show_event_title=True,
        size_table_or_pickup="xlarge",
        size_order_lines="large",
        show_price=False,
        bottom_line="",
    )


def _customer_profile_model() -> ReceiptProfileConfig:
    return ReceiptProfileConfig(
        logo_enabled=True,
        show_event_title=True,
        size_table_or_pickup="xlarge",
        size_order_lines="normal",
        show_price=False,
        bottom_line="",
    )


def _payment_profile_model() -> PaymentReceiptProfileConfig:
    return PaymentReceiptProfileConfig(
        logo_enabled=True,
        show_event_title=True,
        size_order_lines="normal",
        bottom_line="",
    )


class ReceiptPrintingConfig(BaseModel):
    station_receipt: ReceiptProfileConfig = Field(default_factory=_station_profile_model)
    customer_receipt: ReceiptProfileConfig = Field(default_factory=_customer_profile_model)
    payment_receipt: PaymentReceiptProfileConfig = Field(default_factory=_payment_profile_model)


class EventReceiptPrintingConfig(ReceiptPrintingConfig):
    label_event_title: str = ""

    @field_validator("label_event_title")
    @classmethod
    def _limit_label(cls, v: str) -> str:
        text = (v or "").strip()
        if len(text) > MAX_LABEL_EVENT_TITLE_CHARS:
            raise ValueError(f"label_event_title max {MAX_LABEL_EVENT_TITLE_CHARS} characters")
        return text


class ReceiptPrintingRead(BaseModel):
    config: EventReceiptPrintingConfig | ReceiptPrintingConfig
    has_receipt_logo: bool = False


class ReceiptPrintingConfigUpdate(BaseModel):
    config: ReceiptPrintingConfig


class EventReceiptPrintingUpdate(BaseModel):
    config: EventReceiptPrintingConfig


def default_station_profile() -> dict[str, Any]:
    return _station_profile_model().model_dump()


def default_customer_profile() -> dict[str, Any]:
    return _customer_profile_model().model_dump()


def default_payment_profile() -> dict[str, Any]:
    return _payment_profile_model().model_dump()


def default_vendor_printing_config() -> dict[str, Any]:
    return ReceiptPrintingConfig().model_dump()


def default_event_printing_config() -> dict[str, Any]:
    return EventReceiptPrintingConfig().model_dump()


def _config_dict(entity) -> dict[str, Any]:
    raw = getattr(entity, "receipt_printing_config", None)
    if isinstance(raw, dict) and raw:
        return copy.deepcopy(raw)
    return {}


def normalize_vendor_config(raw: dict | None) -> dict[str, Any]:
    base = default_vendor_printing_config()
    if not raw:
        return base
    merged = ReceiptPrintingConfig.model_validate({**base, **raw})
    return merged.model_dump()


def normalize_org_config(raw: dict | None) -> dict[str, Any]:
    return normalize_vendor_config(raw)


def normalize_event_config(raw: dict | None) -> dict[str, Any]:
    base = default_event_printing_config()
    if not raw:
        return base
    merged = EventReceiptPrintingConfig.model_validate({**base, **raw})
    return merged.model_dump()


def _safe_normalize_vendor_config(raw: dict | None) -> dict[str, Any]:
    try:
        return normalize_vendor_config(raw)
    except ValidationError:
        return default_vendor_printing_config()


def _safe_normalize_event_config(raw: dict | None) -> dict[str, Any]:
    try:
        return normalize_event_config(raw)
    except ValidationError:
        return default_event_printing_config()


def has_receipt_logo(entity) -> bool:
    mime = getattr(entity, "receipt_logo_mime", None)
    data = getattr(entity, "receipt_logo_data", None)
    return bool(mime and data)


def receipt_logo_bytes(entity) -> tuple[str, bytes] | None:
    if not has_receipt_logo(entity):
        return None
    return entity.receipt_logo_mime, base64.b64decode(entity.receipt_logo_data)


def store_receipt_logo(entity, mime: str, raw_bytes: bytes) -> None:
    normalized = (mime or "").split(";")[0].strip().lower()
    if normalized == "image/jpg":
        normalized = "image/jpeg"
    if normalized not in ALLOWED_RECEIPT_LOGO_MIMES:
        raise ValueError("File must be PNG or JPEG")
    if len(raw_bytes) > MAX_RECEIPT_LOGO_BYTES:
        raise ValueError(f"File too large (max {MAX_RECEIPT_LOGO_BYTES // 1024} KB)")
    entity.receipt_logo_mime = normalized
    entity.receipt_logo_data = base64.b64encode(raw_bytes).decode("ascii")


def clear_receipt_logo(entity) -> None:
    entity.receipt_logo_mime = None
    entity.receipt_logo_data = None


def copy_receipt_printing(source, target, *, include_event_label: bool = False) -> None:
    """Snapshot receipt config and logo from source entity onto target."""
    raw = _config_dict(source)
    if include_event_label:
        target.receipt_printing_config = _safe_normalize_event_config(raw)
    else:
        # Drop event-only fields when copying to org/vendor shapes
        raw.pop("label_event_title", None)
        target.receipt_printing_config = _safe_normalize_vendor_config(raw)
    if has_receipt_logo(source):
        target.receipt_logo_mime = source.receipt_logo_mime
        target.receipt_logo_data = source.receipt_logo_data
    else:
        clear_receipt_logo(target)


def copy_receipt_printing_from_hire_company(hire_company, organisation) -> None:
    if _config_dict(hire_company) or has_receipt_logo(hire_company):
        copy_receipt_printing(hire_company, organisation, include_event_label=False)
    else:
        organisation.receipt_printing_config = default_vendor_printing_config()
        clear_receipt_logo(organisation)


def copy_receipt_printing_from_organisation(organisation, event) -> None:
    if _config_dict(organisation) or has_receipt_logo(organisation):
        org_cfg = _safe_normalize_vendor_config(_config_dict(organisation))
        event_cfg = {**default_event_printing_config(), **org_cfg}
        event.receipt_printing_config = _safe_normalize_event_config(event_cfg)
        if has_receipt_logo(organisation):
            event.receipt_logo_mime = organisation.receipt_logo_mime
            event.receipt_logo_data = organisation.receipt_logo_data
        else:
            clear_receipt_logo(event)
    else:
        event.receipt_printing_config = default_event_printing_config()
        clear_receipt_logo(event)


def read_printing_response(entity, *, is_event: bool = False) -> ReceiptPrintingRead:
    raw = _config_dict(entity)
    if is_event:
        config = EventReceiptPrintingConfig.model_validate(normalize_event_config(raw))
    else:
        config = ReceiptPrintingConfig.model_validate(normalize_org_config(raw))
    return ReceiptPrintingRead(config=config, has_receipt_logo=has_receipt_logo(entity))


def apply_vendor_or_org_printing_update(entity, body: ReceiptPrintingConfigUpdate) -> None:
    entity.receipt_printing_config = body.config.model_dump()


def apply_event_printing_update(entity, body: EventReceiptPrintingUpdate) -> None:
    entity.receipt_printing_config = body.config.model_dump()


def printing_bundle_dict(event) -> dict[str, Any]:
    """Resolved printing block for Pi edge bundle (event snapshot only)."""
    cfg = normalize_event_config(_config_dict(event))
    out: dict[str, Any] = {
        "label_event_title": cfg.get("label_event_title") or "",
        "station_receipt": cfg.get("station_receipt") or default_station_profile(),
        "customer_receipt": cfg.get("customer_receipt") or default_customer_profile(),
        "payment_receipt": cfg.get("payment_receipt") or default_payment_profile(),
    }
    if has_receipt_logo(event):
        out["logo_base64"] = event.receipt_logo_data
        out["receipt_logo_base64"] = event.receipt_logo_data
    return out
