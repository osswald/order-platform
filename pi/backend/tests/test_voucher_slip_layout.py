"""Voucher slips use the same ESC/POS layout as station/pickup receipts."""

from app.print_worker import build_voucher_slip_text


def _slip_text(slip: bytes) -> str:
    return slip.decode("cp858", errors="replace")


def test_voucher_slip_unified_layout():
    slip = build_voucher_slip_text(
        event_name="Sommerfest",
        voucher_name="Gutschein 20",
        value_cents=2000,
        currency="CHF",
        copy_index=1,
        copy_total=2,
        generated_at="2024-01-22T10:07:00+00:00",
        event={
            "configuration": {
                "printing": {
                    "station_receipt": {
                        "logo_enabled": False,
                        "size_table_or_pickup": "xlarge",
                        "size_order_lines": "large",
                    }
                }
            }
        },
    )
    text = _slip_text(slip)
    assert "GUTSCHEIN" in text
    assert "Sommerfest" in text
    assert "22.01.2024 11:07 Uhr" in text
    assert "Kopie 1/2" in text
    assert "20.00" not in text
    assert "Gutschein 20" in text
    assert "Einloesung bei Zahlung." in text
    assert "Danke für Ihre Bestellung!" not in text
    assert " 0.00" not in text
    assert bytes([0x1D, 0x21, 0x22]) in slip  # 3×3 char size
    assert bytes([0x1D, 0x21, 0x77]) not in slip  # not full 8×8 hero
