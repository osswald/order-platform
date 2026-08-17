"""Unit tests for SumUp Merchant Sales checkout description."""

from app.sumup_checkout_description import sumup_checkout_description


def test_joins_event_solo_and_waiter():
    assert sumup_checkout_description("Dorffest", "Bar", "Anna") == "Dorffest · Bar · Anna"


def test_omits_blank_waiter():
    assert sumup_checkout_description("Dorffest", "Bar", None) == "Dorffest · Bar"
    assert sumup_checkout_description("Dorffest", "Bar", "  ") == "Dorffest · Bar"


def test_skips_blank_parts():
    assert sumup_checkout_description("  ", "Bar", "Anna") == "Bar · Anna"
    assert sumup_checkout_description("Dorffest", None, "Anna") == "Dorffest · Anna"


def test_omits_description_when_nothing_remains():
    assert sumup_checkout_description(None, None, None) is None
    assert sumup_checkout_description("  ", "", None) is None


def test_truncates_to_90_characters_with_ellipsis():
    event = "A" * 50
    solo = "B" * 50
    waiter = "C" * 50
    out = sumup_checkout_description(event, solo, waiter)
    assert out is not None
    assert len(out) == 90
    assert out.endswith("…")
    assert out.startswith("A")
    joined = f"{event} · {solo} · {waiter}"
    assert len(joined) > 90
    assert out == joined[:89] + "…"
