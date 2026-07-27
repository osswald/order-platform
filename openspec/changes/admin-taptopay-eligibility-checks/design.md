## Context

Pi Admin already shows a single Tap to Pay readiness line from `AndroidTerminal.supportsTapToPay()` (`ready` / `ready_simulated` / `location_missing` / `unsupported` / `error`). That call maps Stripe’s `Terminal.supportsReadersOfType` plus a location-permission gate into one coarse code. Field support cannot see which Stripe device criteria failed.

Stripe documents Tap to Pay on Android requirements (NFC + ARM, Android 13+, hardware keystore v100+, GMS/Play Store, recent security patch, not rooted / locked bootloader, unmodified OS, Developer options off for production, stable internet). `supportsReadersOfType` returns a boolean (+ optional error) in ~10 ms; discover/connect enforce additional soft criteria. The Admin checklist should combine **local PackageManager / Settings probes** with the **SDK overall result**, without charging a card.

## Goals / Non-Goals

**Goals:**

- Return a structured list of eligibility checks (id + pass/fail + optional detail) from the native readiness path.
- In Pi Admin on Android, when any check fails (or overall status is not ready), show every check with OK / not-OK so support sees both failures and passes.
- When overall status is ready (or ready simulated), keep the single status line and hide the checklist.
- Preserve payment-picker behaviour: ignore `checks` for enable/disable; older APKs without `checks` keep fail-open for device support.

**Non-Goals:**

- Guaranteeing a real card charge will succeed (Connect onboarding, network mid-payment, etc.).
- Root / bootloader / “unmodified OS” attestation with high confidence (unreliable heuristics → omit or mark unknown, not hard-fail alone).
- Changing Karte picker hints or cloud/Pi APIs.
- iOS Tap to Pay.

## Decisions

### 1. Extend `supportsTapToPay()` JSON with optional `checks[]` (no new bridge method)

**Choice:** Keep one method; add:

```json
{
  "ok": true,
  "supported": false,
  "code": "unsupported",
  "error": "…",
  "simulated": false,
  "checks": [
    { "id": "location", "ok": true },
    { "id": "android_version", "ok": true },
    { "id": "nfc", "ok": false, "detail": "Kein NFC" },
    { "id": "hardware_keystore", "ok": true },
    { "id": "gms", "ok": true },
    { "id": "security_patch", "ok": true },
    { "id": "developer_options", "ok": true },
    { "id": "internet", "ok": true },
    { "id": "sdk_support", "ok": false, "detail": "…" }
  ]
}
```

**Why:** Admin and picker already call this; picker can ignore unknown fields. Avoids a second Terminal init path.

**Alternatives:** Separate `getTapToPayEligibility()` — clearer separation, more bridge surface and duplicate init. Rejected for YAGNI.

### 2. Fixed check set (local probes + SDK)

| id | Probe | Pass when |
|----|--------|-----------|
| `location` | Fine or coarse location granted | Permission present |
| `android_version` | `SDK_INT` | ≥ 33 (Android 13+) |
| `nfc` | `FEATURE_NFC` | Feature present |
| `hardware_keystore` | `FEATURE_HARDWARE_KEYSTORE` | Present with version ≥ 100 when version is available |
| `gms` | Play Store / GMS package present | At least one present |
| `security_patch` | `Build.VERSION.SECURITY_PATCH` | Patch date within last 12 months (parseable) |
| `developer_options` | `Settings.Global.DEVELOPMENT_SETTINGS_ENABLED` | Disabled in release; in debug builds always `ok: true` with optional detail that debug uses simulated reader |
| `internet` | Active network capability | Connected (best-effort; not a full Stripe connectivity probe) |
| `sdk_support` | `supportsReadersOfType` | `isSupported` after Terminal init |

Skip `sdk_support` evaluation when location is missing (cannot init/check meaningfully the same way today); still emit the check as `ok: false` with detail that location is required, or omit SDK call and mark `ok: false` / `skipped` — prefer always including the id with `ok: false` and a clear detail so the Admin list stays complete.

Do **not** include rooted/bootloader/unmodified-OS as hard checklist rows in v1 (false positives hurt field trust).

### 3. Overall `code` stays authoritative; checklist is diagnostic

**Choice:** Existing mapping (`ready` / `location_missing` / `unsupported` / …) unchanged. `checks` is additive diagnostics. Admin shows the list when `code` is not `ready` or `ready_simulated`, **or** when any `checks[].ok === false` (defensive).

**Why:** Matches “only list when there are checks that are not ok” while keeping the summary label.

### 4. Pi Admin UI

**Choice:** Keep `Tap to Pay: {label}` summary. Below it, when showing the list, render a compact muted list (e.g. `✓ Android 13+` / `✗ NFC`) using stable German labels keyed by `id`. No new Admin route.

**Why:** Fits existing version-line footer; support sees reasons without leaving Admin.

### 5. Tests

**Choice:** Unit-test check evaluation helpers in Android (or pure Kotlin functions injectable with fakes) and Pi `taptoPayStatus` / `AdminHubView` for parse + conditional render. Prefer extracting probe logic from the `@JavascriptInterface` method for testability.

## Risks / Trade-offs

- **[Risk] Local checks disagree with Stripe SDK** → Mitigation: always include `sdk_support`; label the UI as device eligibility diagnostics, not a payment guarantee (same caveat as today).
- **[Risk] Security-patch / internet false negatives** → Mitigation: best-effort; show detail string; do not change picker gates based on these alone (picker continues to use overall `supported` / location only).
- **[Risk] Older APKs without `checks`** → Mitigation: Admin shows summary only (current behaviour); no crash on missing array.
- **[Risk] Checklist noise when ready** → Mitigation: hide list when all ok / ready codes.

## Migration Plan

1. Ship Android bridge with `checks` (backward-compatible JSON).
2. Ship Pi frontend Admin checklist behind presence of `checks`.
3. No DB/migration. Rollback: revert frontend (summary-only) or ignore `checks`.

## Open Questions

- None blocking; rooted/bootloader rows deferred unless support asks for them after v1.
