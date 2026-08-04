## Why

Waiters bind a SumUp Solo at login, but device batteries often die mid-shift. Today the only way to switch is **Kellner wechseln** → re-login (PIN again, and a shift-close prompt when shift settlement is enabled). Cash registers stay powered, so this gap is waiter-only.

## What Changes

- On the waiter hub, show the currently assigned SumUp device label when `sumup_connected` applies and a reader is bound.
- Let the logged-in waiter change that assignment via a hub action that reuses the same labelled-reader picker as login.
- Persist the new reader on the existing waiter session; do **not** end the shift, clear the session, or require PIN again.
- Leave cash-register default reader binding and login-time selection unchanged.
- Update `sumup-cloud-payments` so waiter reader binding can change mid-session from the hub, not only via re-login.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `sumup-cloud-payments`: Waiter SumUp device assignment may be changed from the waiter hub without logging out; hub surfaces the current device label.

## Impact

- **Pi frontend**: `WaiterHubView` (+ tests); waiter session update helper; reuse `sumupReaders` picker helpers from login.
- **Specs**: delta on `sumup-cloud-payments` (waiter login requirement + new hub-switch requirement).
- No cloud API, Pi backend, or cash-register UI changes.
