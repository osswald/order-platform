## Context

See `proposal.md` for motivation. Today SumUp connected collection is centralized in Pi frontend helpers (`sumupCheckout` / `resolvePayment`) with a global `terminalPaymentBusy` overlay in `App.vue` that shows “Karte an das Gerät halten…” and has no cancel control. Twint already has cancel → `'cancelled'` → suppressed error toast. Edge terminate (`POST /v1/sumup/terminate`) and status polling already exist; living `sumup-cloud-payments` already requires terminate while awaiting cardholder action, but the POS never exposes it. Split-pay sets `paying` only around the settle HTTP call *after* SumUp returns, so a second green-check can start during the wait — the likely root of “nothing to settle” after a reported failure.

## Goals / Non-Goals

**Goals:**
- Shared waiting overlay: cancel + clear in-progress state for every `sumup_connected` entry point
- Prominent failure UI (sheet/full-screen), dismiss → back to settle/pay
- Attempt-scoped abort so cancel never settles; lock pay for the whole collection window
- Reuse existing terminate/status APIs; Pi frontend–centric change

**Non-Goals:**
- Cloud admin SumUp device UI
- New order-level `payment_status` values (`pending` / `failed`)
- Auto-restart SumUp after failure dismiss
- Changing SumUp merchant/connect/reader catalog behavior
- Recovering/reconciling a late SumUp `paid` after local cancel into the order automatically (out of band / support)

## Decisions

### 1. Failure and cancel UX live on the shared App overlay, not per settle view
**Choice:** Extend the existing `terminalPaymentBusy` overlay in `App.vue` with Cancel, and add a sibling failure sheet driven by the same payment-resolution layer.  
**Why:** All `sumup_connected` paths already funnel through `resolvePaymentsForAmount` → overlay; one UI covers register, table, collective, and legacy order pay.  
**Alternatives:** Per-view dialogs (easy to miss an entry point); navigate to a dedicated route (heavier, breaks split-pay context).

### 2. Abort via attempt token + `terminate`, mirrored on Twint cancel semantics
**Choice:** Give each SumUp collection an attempt id / `AbortSignal`. Cancel sets aborted, calls `terminateSumupCheckout` (best effort), rejects with a dedicated `cancelled` error that callers already treat as quiet. Polling checks abort between ticks and refuses to return success after abort.  
**Why:** Matches Twint; prevents late poll success from resolving into settle after cancel.  
**Alternatives:** Only terminate without aborting the promise (race remains); only abort without terminate (reader keeps waiting).

### 3. Failure sheet, not toast-only; dismiss does not auto-retry SumUp
**Choice:** On non-cancel failure/timeout, hide waiting overlay, show a large failure sheet (title + short reason + dismiss). Dismiss returns to settle; operator taps pay again and can pick any method.  
**Why:** Operator asked for bigger than toast; auto-restart would trap them on card when they may want cash/TWINT.  
**Alternatives:** Auto “Erneut versuchen” that immediately recreates checkout; toast + banner (still easy to miss).

### 4. Lock `paying` / busy for the entire collection, not only settle POST
**Choice:** Set the split-pay / order-pay busy flag before starting SumUp collection (or equivalently gate green-check on `terminalPaymentBusy`). Disable pay controls while busy.  
**Why:** Addresses the double-submit hypothesis for empty settle after a “failed” attempt.  
**Alternatives:** Queue second tap (confusing); debounce only (still allows overlap across views).

### 5. Late `paid` after cancel is ignored by that attempt (no auto-settle)
**Choice:** Cancelled attempts never call settle even if a subsequent status read would show paid. Document as known edge case (guest charged at SumUp, order unpaid in Vendiqo) for rare race; mitigation is fast terminate + short poll abort.  
**Why:** Auto-settling after cancel surprises the operator and can pay the wrong selection. Manual recovery is safer.  
**Alternatives:** Prompt “Zahlung bei SumUp erfolgreich — übernehmen?” (nice follow-up, not in this change).

### 6. Spec split: new UX capability + small deltas on existing payment specs
**Choice:** New `sumup-connected-payment-ux` for POS UX; ADDED requirements on `sumup-cloud-payments` and `register-order-settlement` for unpaid-after-fail and split-pay retention.  
**Why:** Keeps merchant/lifecycle specs stable while making operator UX testable as its own contract.

## Risks / Trade-offs

- **[Risk] Late SumUp success after cancel → guest charged, order open in Vendiqo** → Mitigation: terminate immediately on cancel; abort poll; optional future reconcile prompt (non-goal now).
- **[Risk] Terminate fails (network) while local UI already cancelled** → Mitigation: best-effort terminate + still abort local attempt; timeout path already terminates today.
- **[Risk] Failure sheet vs customer-display restore timing** → Mitigation: keep existing `onSumupHide` / restore cart display on both fail and cancel (already required by `customer-display-realtime`).
- **[Trade-off] No auto-retry** → One extra tap after failure; clearer method choice.

## Migration Plan

- Deploy Pi frontend (and Pi backend only if tiny proxy/error mapping changes). No DB migration. No cloud OpenAPI regen expected.
- Rollback: revert Pi frontend; terminate API remains harmless.
- No feature flag required for first ship; behavior is additive UX on existing flows.

## Open Questions

None that block implementation. Optional follow-up: operator prompt when SumUp reports paid after local cancel (Decision 5 alternative).
