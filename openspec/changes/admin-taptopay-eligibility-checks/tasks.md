## 1. Android eligibility probes (tests first)

- [x] 1.1 Add unit tests for Tap to Pay eligibility probe helpers (Android version, NFC, keystore, GMS/Play Store, security patch age, developer options, internet, location) covering pass and fail cases
- [x] 1.2 Implement pure/helper probe functions used by the bridge (injectable context where needed for testability)
- [x] 1.3 Extend `supportsTapToPay()` tests (or helper composition tests) so the response always includes a stable `checks` array with `id` / `ok` / optional `detail`, including `sdk_support`

## 2. Android bridge wiring

- [x] 2.1 Wire probes + existing `supportsReadersOfType` into `StripeTerminalBridge.supportsTapToPay()` without changing top-level `code` / `supported` / location semantics for the payment picker
- [x] 2.2 Ensure location-missing and unsupported paths still return full `checks` lists; debug builds keep simulated SDK config and developer-options check behaviour per design

## 3. Pi frontend status parsing (tests first)

- [x] 3.1 Extend `taptoPayStatus` tests for parsing `checks`, detecting “has failures”, and German labels per check id
- [x] 3.2 Map bridge `checks` onto `TapToPayAdminStatus` (or adjacent type) without breaking existing status codes / cache / force-refresh behaviour
- [x] 3.3 Confirm payment-picker / `androidTerminal` paths ignore `checks` (no new enable/disable gates)

## 4. Pi Admin UI

- [x] 4.1 Extend `AdminHubView` tests: checklist visible when any check fails; hidden when ready / ready_simulated; graceful when `checks` absent
- [x] 4.2 Render eligibility checklist under the Tap to Pay summary line (pass/fail per item, German labels) only when there are failed checks
- [x] 4.3 Update `docs/stripe-connect-terminal.md` Admin section to mention the diagnostic checklist

## 5. Verify

- [x] 5.1 Run Pi frontend tests for touched files and Android unit tests for eligibility helpers
- [x] 5.2 Run lint for touched areas (`./scripts/lint.sh --staged` or equivalent paths)
