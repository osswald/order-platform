# Vendiqo Waiter (Android)

Native Android WebView wrapper for [`pi/frontend`](../pi/frontend).

- Requires **Android 12+** (`minSdk 31`).
- Bundles the Vue frontend into the APK via Gradle (`copyPiFrontendAssets`).
- Default Pi API URL: **`http://192.168.192.10`** (production Pi nginx on port 80; override at build or in Admin).
- Exposes `window.AndroidPrinter` for paired Bluetooth Classic ESC/POS printers.
- WebView uses **edge-to-edge** layout with system bar insets so UI is not hidden behind the navigation bar.
- Bundled UI is served via `WebViewAssetLoader` (`https://appassets.androidplatform.net/public/…`) so Vite ES modules load correctly (plain `file://` shows a white screen).

## Prerequisites

- **JDK 17** (required by Gradle 9)
- **Android SDK** with API 35 (Android Studio recommended)
- **Node.js + npm** (frontend is built during Gradle `preBuild`)
- Pi reachable on the LAN at **`http://192.168.192.10`** (same Wi‑Fi/VLAN as the phone)

Set `ANDROID_HOME` if building from the command line outside Android Studio.

Gradle resolves `npm` via [`scripts/resolve-npm.sh`](scripts/resolve-npm.sh) (PATH plus common Homebrew/nvm locations), so Android Studio builds work even when the IDE’s PATH omits Node. If resolution fails, install Node.js or open Studio from a terminal where `npm` works (`open -a "Android Studio"`).

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
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Pi backend URL

The bundled frontend is built with [`pi/frontend/.env.android`](../pi/frontend/.env.android) (`VITE_API_BASE=http://192.168.192.10`). API calls go to `/v1/…` on that host (nginx proxies to `pi-backend`).

Three ways to change the URL:

1. **Build override** — different Pi IP on your LAN:

   ```sh
   ./gradlew assembleDebug -PVITE_API_BASE=http://192.168.192.20
   ```

2. **After install** — Admin → **Pi-API Basis-URL** → save (stored in `localStorage` on the device).

3. **Remote WebView URL** (optional) — load the Pi PWA from nginx instead of bundled assets:

   ```sh
   adb shell am start -n ch.vendiqo.app/.MainActivity \
     --es frontend_url "http://192.168.192.10"
   ```

   Still set **Pi-API** to `http://192.168.192.10` in Admin if the WebView origin does not match your API host.

### Physical device (typical)

1. Install the APK (`adb install` or Android Studio).
2. Open the app (bundled UI by default).
3. Pair/setup Pi if needed; in **Admin**, confirm API `http://192.168.192.10` and run **Konfiguration laden**.

Do **not** use `localhost:5174` on a real phone — that only works with `adb reverse` to a Mac dev server.

### Android emulator + Mac dev server (live Vite)

Debug APKs use the **bundled** frontend by default. For hot-reload against Vite on your Mac:

```sh
cd ../pi/frontend && npm run dev
```

Emulator port forwarding:

```sh
adb reverse tcp:5174 tcp:5174
adb reverse tcp:8001 tcp:8001
```

Launch with the dev frontend URL (emulator `10.0.2.2` = host loopback):

```sh
adb shell am start -n ch.vendiqo.app/.MainActivity \
  --ez use_dev_frontend true \
  --es frontend_url "http://10.0.2.2:5174"
```

Or only the dev flag if `DEV_FRONTEND_URL` is set in the debug build:

```sh
adb shell am start -n ch.vendiqo.app/.MainActivity --ez use_dev_frontend true
```

## Bluetooth receipt printer

1. Pair the ESC/POS printer in Android **Settings → Bluetooth**.
2. Open the app → Kellner hub → **Bluetooth Drucker**.
3. Grant Bluetooth permissions, select the paired printer, run **Testbeleg drucken**.

Printer selection is stored only on the device.

After a payment, the app asks whether to print a **Zahlungsbeleg**. If a Bluetooth printer is paired, printing uses the phone; **station printers are only offered when no Bluetooth printer is selected**. Pair a printer under Kellner hub → **Bluetooth Drucker** before service.

## Stripe Tap to Pay

The app exposes `window.AndroidTerminal` as a JavaScript bridge ([`MainActivity.kt`](app/src/main/java/ch/vendiqo/app/MainActivity.kt)). When an event has the `stripe_terminal` payment type and the organisation is Stripe Connect–onboarded, the Pi PWA uses this bridge for card payments on the device.

The Pi backend proxies Stripe Terminal API calls to the cloud edge API. See [docs/stripe-connect-terminal.md](../docs/stripe-connect-terminal.md) for the full Connect + Terminal setup and test flow.

Requirements:

- Android 12+ (same as the app)
- Stripe Connect onboarding completed in cloud admin for the organisation
- `stripe_terminal` enabled in the event's payment types

## Frontend-only rebuild

To iterate on UI without a full Gradle cycle:

```sh
cd ../pi/frontend
npm run build -- --mode android
```

Then run `./gradlew assembleDebug` again (copies `dist/` into assets).

## Project layout

| Path | Purpose |
|------|---------|
| `app/src/main/java/ch/vendiqo/app/MainActivity.kt` | WebView shell, insets, load URL |
| `app/src/main/java/ch/vendiqo/app/BluetoothPrinterBridge.kt` | JS bridge for ESC/POS |
| `app/src/main/java/ch/vendiqo/app/StripeTerminalBridge.kt` | JS bridge for Stripe Tap to Pay (`AndroidTerminal`) |
| `app/src/main/assets/public/` | Bundled frontend (generated, gitignored) |
| `app/src/main/res/mipmap-*/` | Launcher icons |
| `keystore.properties` | Release signing secrets (gitignored) |
