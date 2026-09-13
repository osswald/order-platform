## 1. Pi display JPEG

- [x] 1.1 Add failing tests that a large original is served as JPEG with longest edge ≤ 1920 and the store file is unchanged
- [x] 1.2 Implement `jpeg_bytes_for_display` and use it on `GET /v1/screensaver/{sha256}`

## 2. Customer display blob loading

- [x] 2.1 Add failing tests for fetch + blob object URLs and revoke on cleanup
- [x] 2.2 Load idle gallery via `loadScreensaverObjectUrls` in `RegisterDisplayView`; fall back to welcome when none load

## 3. Android WebView intercept

- [x] 3.1 Restrict `shouldInterceptRequest` to `appassets.androidplatform.net` so Pi HTTP is not asset-loaded

## 4. Verification

- [x] 4.1 Run Pi backend and Pi frontend tests for touched areas
- [x] 4.2 Run `./scripts/lint.sh` on changed areas
