## Context

Waiter SumUp reader binding is client-side only: `LoginView` stores `sumupReaderId` / `sumupReaderLabel` on the waiter session; `resolveActiveSumupReaderId` prefers that for `sumup_connected` checkouts. Spec language today says the binding lasts until login changes it. Cash-register defaults are powered devices and stay out of scope.

## Goals / Non-Goals

**Goals:**

- Let a logged-in waiter change their SumUp device from the waiter hub without logout, PIN, or shift end.
- Show the current device label on the hub when a binding applies.
- Reuse the same labelled-reader list as login; keep subsequent payments on the updated session reader.

**Non-Goals:**

- Cash-register reader rebinding or mid-shift register picker.
- Server-side “who holds which reader” locking or exclusive assignment.
- Changing login-time picker behaviour (still required when multiple readers).
- Pay-screen reactive switch on checkout failure (can be a follow-up).
- Backend/API or cloud admin changes.

## Decisions

1. **Hub-only UI surface**  
   Show current label under the hub subtitle (e.g. `Event · Waiter · SumUp: Bar 2`) and a footer/action control **SumUp-Gerät wechseln** that opens an in-hub picker (same row list pattern as `LoginView`).  
   *Alternatives:* pay-failure only (too late / harder to discover); always pick at pay (defeats login binding).

2. **No PIN re-auth**  
   The waiter is already authenticated for the tablet session; swapping hardware is an operational action, not a identity change. Requiring PIN would reintroduce friction we are removing.  
   *Alternative:* PIN confirm — rejected for this change; tablet unlock / shared-device policy remains a venue concern.

3. **Session patch, not re-login**  
   Update `waiter` via existing `setWaiter` / session persist with new `sumupReaderId` + `sumupReaderLabel`. Do not call `maybeEndShiftOnSwitch` or clear the waiter.  
   *Alternative:* route through login with prefilled waiter — still hits PIN and shift dialog.

4. **Visibility rules**  
   Show label + switch only when `eventNeedsSumupReaderPicker` would apply for the event (i.e. `sumup_connected` enabled and at least one org reader). If exactly one reader exists, still allow switch only when more than one is listed; with a single reader the control can be omitted (nothing to switch to). Prefer: show label whenever bound; show switch when `readers.length > 1`.

5. **In-flight checkout**  
   Switching mid-await would be rare (user is on pay UI, not hub). No special cancel-on-switch; if they leave pay and switch on hub, the next checkout uses the new reader. Document as acceptable.

## Risks / Trade-offs

- **[Shared tablet]** Anyone with an open waiter session can reassign the Solo without PIN → Mitigation: same trust model as placing orders; venues that share tablets already use Kellner wechseln.
- **[Concurrent readers]** Two waiters can still pick the same Solo; SumUp rejects overlapping checkouts → Mitigation: unchanged; labels + hub visibility help staff coordinate.
- **[Stale label]** Bundle refresh could rename/unpair a reader → Mitigation: resolve label from current bundle on display; if id missing after switch attempt, show error and keep previous binding.

## Migration Plan

- Frontend-only deploy; no data migration.
- Rollback: revert Pi frontend change; waiters fall back to re-login via **Kellner wechseln**.

## Open Questions

- None blocking; German copy for the action (`SumUp-Gerät wechseln`) can match login label language during implement.
