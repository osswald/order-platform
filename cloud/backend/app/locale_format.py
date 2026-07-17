"""Shared locale formatting for cloud backend (Babel-backed; mirrors frontend formatLocale.ts)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from babel.dates import format_datetime as babel_format_datetime
from babel.numbers import format_decimal

DEFAULT_TIMEZONE = ZoneInfo("Europe/Zurich")
DATETIME_PATTERN = "dd.MM.yyyy HH:mm"
DATETIME_BUCKET_PATTERN = "dd.MM. HH:mm"
TIME_PATTERN = "HH:mm"
DEFAULT_COUNTRY_CODE = "CH"


def resolve_format_locale(ui_locale: str, country_code: str | None = None) -> str:
    """Map app UI locale + organisation country to a Babel locale tag."""
    primary = (ui_locale or "de").split(",")[0].strip().lower()
    lang = "en" if primary.startswith("en") else "de"
    country = (country_code or DEFAULT_COUNTRY_CODE).strip().upper() or DEFAULT_COUNTRY_CODE
    return f"{lang}_{country}"


def intl_locale(ui_locale: str, country_code: str | None = None) -> str:
    """BCP 47 tag for Intl / vue-i18n formatters."""
    return resolve_format_locale(ui_locale, country_code).replace("_", "-")


def _parse_iso(iso: str | datetime | None) -> datetime | None:
    if iso is None:
        return None
    if isinstance(iso, datetime):
        return iso
    text = str(iso).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _localize_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(DEFAULT_TIMEZONE)


def format_amount(
    cents: int | None,
    locale: str = "de",
    country_code: str | None = None,
) -> str:
    babel_locale = resolve_format_locale(locale, country_code)
    value = (cents or 0) / 100
    return format_decimal(value, locale=babel_locale, format="#,##0.00")


def format_money(
    cents: int | None,
    *,
    locale: str = "de",
    currency: str = "CHF",
    country_code: str | None = None,
) -> str:
    code = (currency or "CHF").upper()
    return f"{code} {format_amount(cents, locale, country_code)}"


def format_price_with_currency(
    amount: float | int | str | None,
    currency: str,
    locale: str = "de",
    country_code: str | None = None,
) -> str:
    code = (currency or "CHF").upper()
    babel_locale = resolve_format_locale(locale, country_code)
    value = float(amount or 0)
    formatted = format_decimal(value, locale=babel_locale, format="#,##0.00")
    return f"{code} {formatted}"


def format_datetime(
    iso: str | datetime | None,
    locale: str = "de",
    country_code: str | None = None,
) -> str:
    dt = _parse_iso(iso)
    if dt is None:
        return "—"
    local = _localize_datetime(dt)
    babel_locale = resolve_format_locale(locale, country_code)
    return babel_format_datetime(
        local,
        DATETIME_PATTERN,
        locale=babel_locale,
        tzinfo=DEFAULT_TIMEZONE,
    )


def format_event_range(
    start_iso: str | datetime | None,
    end_iso: str | datetime | None,
    locale: str = "de",
    country_code: str | None = None,
) -> str:
    start = format_datetime(start_iso, locale, country_code)
    end = format_datetime(end_iso, locale, country_code)
    if start == "—" and end == "—":
        return "—"
    return f"{start} – {end}"


def format_time_label(
    dt: datetime,
    *,
    locale: str = "de",
    country_code: str | None = None,
) -> str:
    local = _localize_datetime(dt)
    babel_locale = resolve_format_locale(locale, country_code)
    return babel_format_datetime(
        local,
        TIME_PATTERN,
        locale=babel_locale,
        tzinfo=DEFAULT_TIMEZONE,
    )


def format_bucket_label(
    dt: datetime,
    *,
    include_date: bool,
    locale: str = "de",
    country_code: str | None = None,
) -> str:
    local = _localize_datetime(dt)
    babel_locale = resolve_format_locale(locale, country_code)
    pattern = DATETIME_BUCKET_PATTERN if include_date else TIME_PATTERN
    return babel_format_datetime(
        local,
        pattern,
        locale=babel_locale,
        tzinfo=DEFAULT_TIMEZONE,
    )
