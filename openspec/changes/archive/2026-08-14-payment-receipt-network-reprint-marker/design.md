## Context

See proposal.md for motivation.

Today:

- `POST /v1/payments/{id}/receipt` accepts `reprint` and `build_payment_receipt_text(..., reprint=True)` writes «Kopie / Nachdruck» after «Beleg».
- Belege → `offerPaymentReceipt({ reprint: true })` passes `reprint` on the Bluetooth path only.
- Network path calls `POST .../receipt/print` with `{ station_uuid }` only. `_create_payment_receipt_print_job` builds a deferred render context without `reprint`, so the worker prints an unmarked original.

Payment-receipt network jobs already go through `pi-receipt-render-offload` (empty `escpos_payload` + `render_context_json`). The fix is to persist `reprint` in that context and honor it in `build_escpos_from_render_context`.

## Goals / Non-Goals

**Goals:**

- Same reprint marker on Bluetooth and network payment-receipt prints when the client requests a reprint.
- Default / omitted `reprint` remains false (first print unmarked).
- Keep existing marker text «Kopie / Nachdruck».

**Non-Goals:**

- Renaming the marker to «Nachdruck» only.
- Auto-detecting reprint without a client flag.
- Changing voucher / station / kitchen slip copy labels.
- Cloud admin or cloud printing.

## Decisions

### 1. Explicit `reprint` on print API (not inferred)

Add optional `reprint: bool = False` to `PaymentReceiptPrintBody`. Frontend sends `true` from Belege (and any future reprint callers); settle/first-print omit or send false.

**Alternatives considered:** Infer reprint from “receipt already printed once” — rejected; first print after settle and history reprint both hit the same endpoints, and inference would be fragile across devices.

### 2. Persist `reprint` in render context

Pass `reprint` into `make_render_context` / `dump_render_context` for `kind="payment_receipt"`, and read it in `build_escpos_from_render_context` when calling `build_payment_receipt_text`.

**Alternatives considered:** Build ESC/POS synchronously on the HTTP path for reprints only — rejected; conflicts with `pi-receipt-render-offload` and duplicates paths.

### 3. Thread flag through PWA network helpers

Extend `printPaymentReceiptToStation` / `printViaNetworkTargets` / `printToStation` to accept and forward `reprint` the same way Bluetooth already does inside `offerPaymentReceipt`.

### 4. Marker text unchanged

Reuse the existing line in `build_payment_receipt_text`; no i18n or copy change in this change.

## Risks / Trade-offs

- [Older clients omit `reprint`] → Mitigation: default `False`; first prints stay correct; only fixed PWA versions mark network reprints.
- [Load-test / auto station prints accidentally set reprint] → Mitigation: leave callers unchanged; only Belege / explicit reprint flows pass `true`.
- [Pi OpenAPI types stale] → Mitigation: update generated types if the repo regenerates Pi OpenAPI for schema changes; otherwise hand-align the request body in the PWA.

## Migration Plan

- Deploy Pi backend + frontend together preferred; backend alone is backward compatible (defaults false).
- Rollback: revert; unmarked network reprints return (Bluetooth marker unchanged).

## Open Questions

None.
