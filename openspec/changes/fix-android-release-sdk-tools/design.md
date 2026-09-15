## Context

See `proposal.md` for why. The Android release workflow uses `android-actions/setup-android@v4` with no `packages` input, so the action defaults to installing `tools` and `platform-tools`. Google’s package index no longer includes `tools`, so `sdkmanager tools` fails and the job stops before Gradle or Play upload. The runner already has cmdline-tools; Gradle/`sdkmanager` only need modern packages (`platform-tools`, then `platforms;android-36`).

## Goals / Non-Goals

**Goals:**
- Make `Android release` pass SDK setup on current GitHub-hosted runners
- Preserve platform 36 install and the rest of the release pipeline

**Non-Goals:**
- Changing app `compileSdk` / `targetSdk`, signing, or Play track logic
- Replacing `android-actions/setup-android` unless a packages tweak is insufficient
- Broader CI migration (caching strategy, self-hosted runners)

## Decisions

### 1. Pass explicit `packages` excluding `tools`
**Choice:** Set `with.packages` on `android-actions/setup-android@v4` to `platform-tools` (space-separated list as required by the action), leaving the existing `sdkmanager "platforms;android-36"` step in place.  
**Why:** Minimal diff; matches the observed failure (`Failed to find package 'tools'`).  
**Alternatives:** Pin an older cmdline-tools that still ships `tools` (fragile); switch to a different setup action (more churn than needed).

### 2. Keep platform install as a separate step
**Choice:** Do not fold `platforms;android-36` into the setup-android `packages` input unless needed for simplicity later.  
**Why:** Current workflow already installs platform 36 explicitly; changing one thing isolates the fix.

## Risks / Trade-offs

- **[Risk] Gradle still needs build-tools / other components not listed** → Mitigation: Android Gradle Plugin usually installs missing build-tools via sdkmanager during `bundleRelease`; if CI then fails on a missing package, add that package to the setup list or an `sdkmanager` step.
- **[Risk] setup-android defaults change again** → Mitigation: keep `packages` explicit so we do not silently reintroduce `tools`.
- **[Trade-off] Manual verification** → Confirm by re-running `workflow_dispatch` on main after merge (or on the PR branch if the workflow is available there).

## Migration Plan

1. Merge workflow YAML change.
2. Re-run **Android release** via `workflow_dispatch` (internal track).
3. Rollback: revert the workflow commit if a different packages set is required.

## Open Questions

None.
