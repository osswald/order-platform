package ch.vendiqo.app

import android.webkit.JavascriptInterface
import org.json.JSONObject

/** Native APK metadata for the Pi PWA Admin hub. */
class AndroidAppBridge {
    @JavascriptInterface
    fun getAppInfo(): String {
        return JSONObject()
            .put("ok", true)
            .put("versionName", BuildConfig.VERSION_NAME)
            .put("versionCode", BuildConfig.VERSION_CODE)
            .toString()
    }
}
