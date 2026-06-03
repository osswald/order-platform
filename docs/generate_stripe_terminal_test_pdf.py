#!/usr/bin/env python3
"""Generate PDF manual test scenarios for Stripe Connect + Terminal."""

from __future__ import annotations

from pathlib import Path

from pdf_test_common import build_test_pdf

OUTPUT = Path(__file__).resolve().parent / "stripe-terminal-test-scenarios.pdf"

STRIPE_GROUPS = [
    ("1. Environment & prerequisites", lambda c: c.startswith("TC-ENV")),
    ("2. Cloud admin (Stripe Connect)", lambda c: c.startswith("TC-C")),
    ("3. Pi backend & PWA", lambda c: c.startswith("TC-P")),
    ("4. Android app (Tap to Pay)", lambda c: c.startswith("TC-A")),
    ("5. End-to-end & reporting", lambda c: c.startswith("TC-E")),
    ("6. Regression (other payment types)", lambda c: c.startswith("TC-R")),
]

TEST_CASES: list[tuple[str, str, list[str], list[str], list[str]]] = [
    (
        "TC-ENV-001",
        "Test environment baseline",
        [
            "Cloud stack running (API + PostgreSQL + admin frontend).",
            "Stripe test mode: restricted key (rk_test_...) with Connect, Terminal, PaymentIntents.",
            "Cloud .env: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_CONNECT_RETURN_URL, STRIPE_CONNECT_REFRESH_URL.",
            "Stripe Dashboard: webhook POST https://<api-host>/stripe/webhooks (account.updated, payment_intent.succeeded).",
            "Tap to Pay on Android enabled for platform and connected accounts.",
            "Tenant admin user; Organisation and Event in order-accepting status (e.g. live).",
            "Pi paired to cloud; bundle sync OK.",
            "Android APK installed; device API 33+, NFC, Google Play services; LAN to Pi.",
        ],
        [
            "Verify cloud GET /health returns ok.",
            "Verify Pi GET /v1/setup/status shows configured.",
            "Verify Pi GET /v1/cloud/reachable returns reachable: true.",
        ],
        ["All checks pass; proceed with functional tests."],
    ),
    (
        "TC-C-001",
        "Stripe not configured on cloud",
        [
            "Cloud backend with STRIPE_SECRET_KEY empty.",
            "Tenant admin logged in.",
        ],
        [
            "Open Organisationen, edit organisation, section Kartenzahlung (Stripe).",
        ],
        [
            "Message that Stripe is not configured; connect actions unavailable or show error.",
        ],
    ),
    (
        "TC-C-002",
        "View Connect status before onboarding",
        [
            "STRIPE_SECRET_KEY set; organisation without stripe_account_id.",
        ],
        [
            "Open organisation detail; review Kartenzahlung (Stripe) chips.",
        ],
        [
            "Zahlungen, Auszahlungen, Angaben show ausstehend.",
            "Mit Stripe verbinden is visible.",
        ],
    ),
    (
        "TC-C-003",
        "Stripe Connect Express onboarding",
        [
            "TC-C-002; Stripe test Connect; return URLs match admin host.",
        ],
        [
            "Click Mit Stripe verbinden; complete Stripe test onboarding.",
            "Return via /settings/stripe/return.",
        ],
        [
            "Redirect to Stripe Account Link and back to admin.",
            "stripe_account_id stored; status updated.",
        ],
    ),
    (
        "TC-C-004",
        "Manual status refresh",
        ["Organisation with stripe_account_id."],
        ["Click Status aktualisieren on organisation detail."],
        [
            "Chips update; message Status aktualisiert.",
            "When ready: Zahlungen aktiv.",
        ],
    ),
    (
        "TC-C-005",
        "Webhook account.updated",
        [
            "Connected org; STRIPE_WEBHOOK_SECRET matches Dashboard.",
            "Stripe CLI or Dashboard test events.",
        ],
        [
            "Send account.updated (e.g. stripe trigger account.updated).",
            "Optional: compare with Status aktualisieren.",
        ],
        [
            "POST /stripe/webhooks returns 200.",
            "Organisation flags match Stripe account state.",
        ],
    ),
    (
        "TC-C-006",
        "Enable Karte on event",
        [
            "Organisation charges_enabled true.",
            "Event editable in cloud admin.",
        ],
        [
            "Event settings: enable Karte (Stripe Terminal); save.",
        ],
        [
            "payment_types includes stripe_terminal.",
            "Visible on Pi after sync (TC-P-003).",
        ],
    ),
    (
        "TC-C-007",
        "Terminal API blocks unready organisation",
        [
            "Event with stripe_terminal; org not charge-ready or no Connect account.",
            "Pi paired.",
        ],
        [
            "POST payment-intent via Pi /v1/terminal/payment-intents (or edge API).",
        ],
        [
            "HTTP 409: account missing or not ready for charges.",
        ],
    ),
    (
        "TC-P-001",
        "Cloud reachable (online)",
        ["Pi paired; cloud up."],
        ["GET /v1/cloud/reachable."],
        ["reachable: true."],
    ),
    (
        "TC-P-002",
        "Cloud unreachable",
        [
            "Pi paired; cloud stopped or blocked.",
        ],
        [
            "GET /v1/cloud/reachable.",
            "Open Zahlungsart in desktop browser PWA.",
        ],
        [
            "reachable: false.",
            "Karte disabled; hint Cloud-Verbindung erforderlich.",
        ],
    ),
    (
        "TC-P-003",
        "Sync exposes stripe_terminal",
        [
            "TC-C-006 done.",
        ],
        [
            "Pi sync pull; waiter opens payment on event.",
        ],
        [
            "Karte in payment picker (disabled on non-Android).",
        ],
    ),
    (
        "TC-P-004",
        "Desktop browser - Karte disabled",
        [
            "stripe_terminal on event; PWA in desktop browser; cloud reachable.",
        ],
        [
            "Login waiter; open Zahlungsart.",
        ],
        [
            "Karte visible, disabled.",
            "Hint: Nur in der Android-App verfügbar.",
        ],
    ),
    (
        "TC-P-005",
        "Reject payment without PaymentIntent id",
        ["Event with stripe_terminal."],
        [
            'POST pay with payments [{"type":"stripe_terminal","amount_cents":500}] only.',
        ],
        [
            "HTTP 400: stripe_payment_intent_id required.",
        ],
    ),
    (
        "TC-A-001",
        "Location permission denied",
        [
            "Android app; stripe_terminal event; cloud up.",
            "Location permission denied for app.",
        ],
        [
            "Open Zahlungsart.",
        ],
        [
            "Karte disabled or payment fails with location message until granted.",
        ],
    ),
    (
        "TC-A-002",
        "Karte enabled in picker",
        [
            "Android; location granted; cloud reachable; Connect ready; event synced.",
        ],
        [
            "Open Zahlungsart on pay flow.",
        ],
        [
            "Karte enabled; no disabled hints.",
        ],
    ),
    (
        "TC-A-003",
        "Tap to Pay - pay table order",
        [
            "TC-A-002; Stripe test card or simulated reader (debug).",
            "Open table with unpaid order.",
        ],
        [
            "Select Karte; complete tap (overlay: Karte an das Gerät halten…).",
        ],
        [
            "Order paid; stripe_payment_intent_id on payment.",
            "Cloud reporting after sync shows Karte.",
        ],
    ),
    (
        "TC-A-004",
        "Tap to Pay - split pay",
        [
            "Split pay view; partial amount; TC-A-002.",
        ],
        [
            "Select lines; pay partial with Karte.",
        ],
        [
            "Partial payment succeeds with pi_ id; remainder still open.",
        ],
    ),
    (
        "TC-A-005",
        "Tap to Pay - cash register",
        [
            "Register mode; TC-A-002.",
        ],
        [
            "Submit register order; pay with Karte.",
        ],
        [
            "Order paid in one flow; PI id present.",
        ],
    ),
    (
        "TC-A-006",
        "Cloud loss during session",
        [
            "App was online; then stop cloud or Pi WAN.",
        ],
        [
            "Re-open Zahlungsart without app restart.",
        ],
        [
            "Karte disabled with cloud hint; cash still works.",
        ],
    ),
    (
        "TC-A-007",
        "Cancel payment picker",
        ["TC-A-002; picker open."],
        ["Tap Abbrechen."],
        ["Order unpaid; no successful card charge."],
    ),
    (
        "TC-A-008",
        "Abort Tap to Pay on device",
        ["TC-A-002; Karte selected."],
        ["Cancel reader flow or fail collection."],
        [
            "Error toast; order unpaid; can retry or use cash.",
        ],
    ),
    (
        "TC-E-001",
        "Full end-to-end happy path",
        [
            "TC-ENV-001, TC-C-003, TC-C-006, TC-P-003, TC-A-003.",
        ],
        [
            "Connect org; enable Karte; sync Pi; pay on Android; sync outbox.",
            "Check cloud event sales / transactions.",
        ],
        [
            "Sale in cloud with Karte (Stripe Terminal).",
            "Stripe Dashboard: PaymentIntent succeeded on connected account.",
        ],
    ),
    (
        "TC-E-002",
        "Multiple payment types same event",
        [
            "Event: cash + stripe_terminal (+ optional twint).",
        ],
        [
            "Pay one order cash; another with Karte on Android.",
        ],
        [
            "Correct types in reporting for each order.",
        ],
    ),
    (
        "TC-E-003",
        "Pay attempt without Connect ready",
        [
            "stripe_terminal on event; org not onboarded.",
        ],
        [
            "Attempt Karte on Android if shown enabled.",
        ],
        [
            "API error 409/502; order not paid.",
        ],
    ),
    (
        "TC-E-004",
        "Payment receipt after card pay",
        [
            "Receipt prompt enabled for event/org.",
            "TC-A-003 done.",
        ],
        [
            "Accept receipt prompt; print Bluetooth or station.",
        ],
        [
            "Receipt prints; shows Karte label.",
        ],
    ),
    (
        "TC-R-001",
        "Cash payment regression",
        ["Event: cash + stripe_terminal."],
        ["Pay with Bargeld on Android or browser."],
        [
            "Success without stripe_payment_intent_id.",
            "No Terminal SDK call.",
        ],
    ),
    (
        "TC-R-002",
        "TWINT regression",
        [
            "Event: twint + QR + stripe_terminal.",
        ],
        [
            "Pay with TWINT.",
        ],
        [
            "TWINT QR flow works independently of Terminal.",
        ],
    ),
]


def build_pdf() -> None:
    build_test_pdf(
        output=OUTPUT,
        title="Stripe Connect & Terminal",
        subtitle="Manual test scenarios for Cloud admin, Pi PWA, and Android Tap to Pay",
        intro=(
            "Run TC-ENV-001 first. Record Pass / Fail / Blocked, build version, Stripe mode (test/live), "
            "and Android device model."
        ),
        groups=STRIPE_GROUPS,
        cases=TEST_CASES,
    )


if __name__ == "__main__":
    build_pdf()
