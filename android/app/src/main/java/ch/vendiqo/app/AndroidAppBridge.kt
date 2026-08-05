package ch.vendiqo.app

import android.os.Handler
import android.webkit.JavascriptInterface
import org.json.JSONObject

/** Native APK metadata and immersive system UI for the Pi PWA. */
class AndroidAppBridge(
    private val immersive: ImmersiveModeController? = null,
    private val mainHandler: Handler? = null,
) {
    @JavascriptInterface
    fun getAppInfo(): String {
        return JSONObject()
            .put("ok", true)
            .put("versionName", BuildConfig.VERSION_NAME)
            .put("versionCode", BuildConfig.VERSION_CODE)
            .toString()
    }

    /**
     * Hide/show status and navigation bars. Invoked from the WebView on the JS thread;
     * window inset changes run on the main thread.
     */
    @JavascriptInterface
    fun setImmersiveMode(enabled: Boolean) {
        val controller = immersive ?: return
        val handler = mainHandler
        if (handler == null) {
            controller.setEnabled(enabled)
            return
        }
        handler.post { controller.setEnabled(enabled) }
    }
}
