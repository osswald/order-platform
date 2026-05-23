# Pi Frontend Android

Native Android WebView wrapper for `pi/frontend`.

- Requires Android 12 or newer (`minSdk 31`).
- Bundles the Vue frontend into the APK via the Gradle `copyPiFrontendAssets` task.
- Defaults the Pi backend URL to `http://192.168.192.10:8001` through the Android Vite build mode.
- Exposes `window.AndroidPrinter` for paired Bluetooth Classic ESC/POS printers.

Build from this directory with a configured Android SDK:

```sh
./gradlew assembleDebug
```

If Gradle is installed without the wrapper:

```sh
gradle assembleDebug
```
