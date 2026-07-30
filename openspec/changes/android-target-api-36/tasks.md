## 1. Tests first

- [x] 1.1 Add a JVM unit test for Terminal locale-config selection (pure helper or package-visible factory) asserting `LocaleConfig.CardLanguagePreferenceIfAvailable` is the chosen init locale config
- [x] 1.2 Add a small test or script assertion that `android/app/build.gradle.kts` declares `compileSdk` / `targetSdk` of 36 (or document why Gradle file assertion is skipped if impractical)

## 2. Gradle and dependencies

- [x] 2.1 Set `compileSdk = 36` and `targetSdk = 36` in `android/app/build.gradle.kts` (leave `minSdk = 33`)
- [x] 2.2 Bump `stripeTerminalVersion` to `5.7.0` for `stripeterminal-taptopay` and `stripeterminal-core`
- [x] 2.3 Ensure Android SDK platform 36 is available locally / in the Android release CI image; install or document if the build fails on missing platform

## 3. Terminal init

- [x] 3.1 Introduce the locale-config helper used by tests and wire `StripeTerminalBridge.ensureTerminalInitialized` to `Terminal.init` with that `LocaleConfig` (replace deprecated no-locale overload)
- [x] 3.2 Resolve any compile/API adjustments required by Terminal 5.7.0 (imports, deprecations) without adopting optional APIs (`processPaymentIntent`, `easyConnect`, surcharging)

## 4. Docs

- [x] 4.1 Update `android/README.md` prerequisites / SDK notes from API 35 to API 36; fix any stale `minSdk 31` wording to match `minSdk 33`
- [x] 4.2 Update Stripe Terminal version references in `docs/stripe-connect-terminal.md` and any design notes that still say `5.5.1` if they are living docs

## 5. Verify

- [x] 5.1 Run Android unit tests (`./gradlew :app:testDebugUnitTest` or project equivalent)
- [x] 5.2 Run `./gradlew assembleDebug` successfully with the new SDK and Stripe artifacts
- [ ] 5.3 Manual QA on a Tap to Pay–capable tablet: discover/connect, test-mode collect; smoke edge insets and rotate/split on `sw600dp+`
- [ ] 5.4 After merge/release upload, confirm Play Console target API warning clears for the new version
