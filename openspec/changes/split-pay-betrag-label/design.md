## Context

See proposal.md — Why. The shared settle UI is `SplitPaySettleScreen.vue`. `useSplitPay` already exposes `remainingItemCount` / `restCents` for the red bar; the green pay button ignores them and always prefixes **Teilbetrag**.

## Goals / Non-Goals

**Goals:**

- Derive the green-bar amount label from whether any open lines remain unselected
- Keep settlement math and pay handlers unchanged

**Non-Goals:**

- i18n extraction of settle-screen strings
- Changing toast copy after partial settle (`Teilbetrag bezahlt…`) unless it falls out naturally
- Backend or API changes

## Decisions

1. **Use `remainingItemCount === 0` (or equivalent rest empty) for Betrag**  
   When the bottom panel has no remaining line quantities, the selection is the full currently open bill → **Betrag**. Otherwise → **Teilbetrag**.  
   **Alternatives considered:** Compare `basketCents === totalCents` — fails when vouchers/fixed credits adjust payable cents while lines remain below; item-count/`restCents` matches the visual split.

2. **Keep German hardcoded in the component**  
   Match existing settle-screen copy style; no vue-i18n pass in this change.

## Risks / Trade-offs

- **[Risk] Empty basket with only voucher/fixed rows** → Mitigation: keep existing disable rules on the pay button; label still follows remaining open article lines / rest.
- **[Trade-off] Toast still says “Teilbetrag bezahlt” after a true partial** — correct; out of scope to reword fully-settled success path beyond existing handling.

## Migration Plan

1. Ship Pi frontend with updated label + tests.
2. No data migration; rollback is revert of the Vue/test change.
