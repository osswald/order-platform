## 1. Tests first (Pi frontend)

- [ ] 1.1 Extend `stripeTerminalAvailability` tests for hint priority: unsupported device, missing location / check failure, and older APK without `supportsTapToPay` (fail open)
- [ ] 1.2 Add/extend `androidTerminal` tests for calling `supportsTapToPay` and parsing `{ ok, supported, error }`
- [ ] 1.3 Update `resolvePayment` / picker tests if they assert readiness composition

## 2. Android bridge

- [ ] 2.1 Implement `supportsTapToPay()` on `StripeTerminalBridge` using `Terminal.supportsReadersOfType` + Tap to Pay discovery config (`isSimulated = BuildConfig.DEBUG`)
- [ ] 2.2 Initialize Terminal lazily for the check; return `ok: false` (not `supported: false`) when location permission is missing
- [ ] 2.3 Leave existing `isAvailable()` semantics unchanged

## 3. Pi PWA availability gating

- [ ] 3.1 Add a typed helper to query `AndroidTerminal.supportsTapToPay` with session cache
- [ ] 3.2 Compose device support into `stripeTerminalPickerEntry` / `stripeTerminalDisabledHint` with German hint «Gerät unterstützt keine Kartenzahlung (Tap to Pay).»
- [ ] 3.3 Preserve order: not Android → cloud → location/check failure → unsupported device; missing bridge method does not disable Karte

## 4. Docs and verification

- [ ] 4.1 Update `docs/stripe-connect-terminal.md` (and optionally `android/README.md`) for the new gate and best-effort limits
- [ ] 4.2 Run Pi frontend tests and `./scripts/lint.sh` (or staged lint) for touched areas
- [ ] 4.3 Manual Android check: supported device enables Karte; unsupported or NFC-incapable device shows the new hint; older-APK fallback remains enabled when only Android+cloud gates pass
