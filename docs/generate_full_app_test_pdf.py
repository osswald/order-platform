#!/usr/bin/env python3
"""Generate full Vendiqo Order Platform manual test scenarios PDF."""

from __future__ import annotations

from pathlib import Path

from full_app_test_cases import FULL_APP_CASES, FULL_APP_GROUPS
from pdf_test_common import build_test_pdf

OUTPUT = Path(__file__).resolve().parent / "vendiqo-full-test-scenarios.pdf"

TITLE = "Vendiqo Order Platform"
SUBTITLE = "Full manual test scenarios — Cloud admin, Pi PWA, Android app"
INTRO = (
    "This document covers functional manual tests for the entire platform: cloud ERP/admin, "
    "Raspberry Pi edge (waiter POS, cash register, kitchen, pickup), and the Android WebView app.\n\n"
    "Record Pass / Fail / Blocked, build version, date, and tester name. Run TC-ENV-* first. "
    "Stripe Terminal cases are in section Cloud/Pi Android Stripe; see also "
    "stripe-terminal-test-scenarios.pdf for card-payment depth.\n\n"
    "Legend: Cloud = browser admin UI; Pi = LAN PWA or Android shell; E2E = data visible in cloud after Pi sync."
)


def main() -> None:
    build_test_pdf(
        output=OUTPUT,
        title=TITLE,
        subtitle=SUBTITLE,
        intro=INTRO,
        groups=FULL_APP_GROUPS,
        cases=FULL_APP_CASES,
    )


if __name__ == "__main__":
    main()
