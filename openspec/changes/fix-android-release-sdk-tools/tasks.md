## 1. Workflow fix

- [ ] 1.1 Update `.github/workflows/android-release.yml` so `android-actions/setup-android@v4` passes an explicit `packages` list that includes `platform-tools` and excludes obsolete `tools`; verify by reading the workflow that the step no longer relies on default packages
- [ ] 1.2 Confirm the existing `sdkmanager "platforms;android-36"` step remains after SDK setup; verify the workflow still installs platform 36 before the Gradle release build

## 2. Validation

- [ ] 2.1 Run `openspec validate fix-android-release-sdk-tools --strict` and ensure it passes
- [ ] 2.2 After merge (or via workflow_dispatch on the PR branch if available), re-run **Android release** and verify the `Set up Android SDK` step succeeds (no `Failed to find package 'tools'`)
