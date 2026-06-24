"""Gross/net/VAT split helpers for fiscal line snapshots."""

from __future__ import annotations


def split_gross_cents(gross_cents: int, rate_percent: float | None) -> tuple[int, int, int]:
    gross = max(0, int(gross_cents or 0))
    rate = float(rate_percent or 0.0)
    if gross == 0 or rate <= 0:
        return gross, gross, 0
    net = round(gross / (1.0 + rate / 100.0))
    vat = gross - net
    return gross, net, vat
