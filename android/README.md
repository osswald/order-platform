# Vendiqo Waiter (Android)

Native Android WebView wrapper for [`pi/frontend`](../pi/frontend).

- Requires **Android 12+** (`minSdk 31`).
- Bundles the Vue frontend into the APK via Gradle (`copyPiFrontendAssets`).
- Default Pi API URL: `http://192.168.192.10:8001` (override at build or in-app).
- Exposes `window.AndroidPrinter` for paired Bluetooth Classic ESC/POS printers.

## Prerequisites

- **JDK 17** (required by Gradle 9)
- **Android SDK** with API 35 (Android Studio recommended)
- **Node.js + npm** (frontend is built during Gradle `preBuild`)
- Pi backend running and reachable from the device on port **8001**

Set `ANDROID_HOME` if building from the command line outside Android Studio.

## Build

From this directory:

```sh
./gradlew assembleDebug
```

Release APK (signed sideload / MDM):

1. Create a keystore once (outside the repo):

   ```sh
   keytool -genkey -v -keystore order-platform-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias release
   ```

2. Copy [`keystore.properties.example`](keystore.properties.example) to `keystore.properties` and fill in paths/passwords.

3. Build:

   ```sh
   ./gradlew assembleRelease
   ```

### Output paths

| Build | APK |
|-------|-----|
| Debug | `app/build/outputs/apk/debug/app-debug.apk` |
| Release | `app/build/outputs/apk/release/app-release.apk` |

### Install on a device

```sh
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Pi backend URL

Three ways to configure the API base URL:

1. **Build default** — Android mode uses `http://192.168.192.10:8001` from [`pi/frontend/src/api.js`](../pi/frontend/src/api.js).
2. **Build override** — pass a Gradle property:

   ```sh
   ./gradlew assembleRelease -PVITE_API_BASE=http://192.168.1.50:8001
   ```

3. **After install** — set the URL in the app (Setup / Admin panel); stored in `localStorage` on the device.

The phone and Pi must be on the same network. Pi backend:

```sh
docker compose -f pi/docker-compose.yml up --build
```

## Bluetooth receipt printer

1. Pair the ESC/POS printer in Android **Settings → Bluetooth**.
2. Open the app → Kellner hub → **Bluetooth Drucker**.
3. Grant Bluetooth permissions, select the paired printer, run **Testbeleg drucken**.

Printer selection is stored only on the device.

## Remote frontend (optional)

For development, load a live Vite dev server instead of bundled assets:

```sh
adb shell am start -n ch.vendiqo.app/.MainActivity --es frontend_url "http://192.168.1.10:5174"
```

## Frontend-only rebuild

To iterate on UI without a full Gradle cycle:

```sh
cd ../pi/frontend
npm run build -- --mode android
```

Then copy `dist/` to `android/app/src/main/assets/public/` or run `./gradlew assembleDebug` again.

## Project layout

| Path | Purpose |
|------|---------|
| `app/src/main/java/ch/vendiqo/app/MainActivity.kt` | WebView shell |
| `app/src/main/java/ch/vendiqo/app/BluetoothPrinterBridge.kt` | JS bridge for ESC/POS |
| `app/src/main/assets/public/` | Bundled frontend (generated, gitignored) |
| `keystore.properties` | Release signing secrets (gitignored) |
