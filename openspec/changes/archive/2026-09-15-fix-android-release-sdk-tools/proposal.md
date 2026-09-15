## Why

The manual **Android release** GitHub Action fails during SDK setup: `android-actions/setup-android@v4` still requests the obsolete `tools` package, and current `sdkmanager` returns `Failed to find package 'tools'`. Play uploads are blocked until CI can install a modern SDK again.

## What Changes

- Configure `Set up Android SDK` so it does **not** install the removed `tools` package (install only packages still published, e.g. `platform-tools`).
- Keep installing `platforms;android-36` (and any other packages Gradle needs) via existing follow-up steps.
- No app/runtime behavior change; CI-only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `android-play-store-release`: Require the Android release workflow’s SDK setup to use currently published SDK packages only (no obsolete `tools` dependency) so `workflow_dispatch` can build and upload an AAB again.

## Impact

- `.github/workflows/android-release.yml` (`android-actions/setup-android@v4` inputs)
- Android release / Play upload path; no Pi/cloud application code
