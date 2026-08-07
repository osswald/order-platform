package ch.vendiqo.app

import android.os.Handler
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject

/** Native APK metadata, immersive system UI, and modem handshake for the Pi PWA. */
class AndroidAppBridge(
    private val immersive: ImmersiveModeController? = null,
    private val mainHandler: Handler? = null,
    private val modemHandshake: ModemHandshakeController? = null,
    private val webViewProvider: (() -> WebView?)? = null,
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

    /**
     * Start the Edi modem handshake (volume bump + sample). Completion is delivered as a
     * `vendiqo-modem-handshake` CustomEvent on `window` with `detail.ok`.
     */
    @JavascriptInterface
    fun playModemHandshake() {
        val run = Runnable {
            val handshake = modemHandshake
            if (handshake == null) {
                dispatchModemHandshakeResult(ok = false)
                return@Runnable
            }
            handshake.start { ok -> dispatchModemHandshakeResult(ok) }
        }
        val handler = mainHandler
        if (handler == null) {
            run.run()
        } else {
            handler.post(run)
        }
    }

    /** Abort an in-flight handshake (Activity teardown). Restores volume. */
    fun cancelModemHandshake() {
        modemHandshake?.cancel()
    }

    private fun dispatchModemHandshakeResult(ok: Boolean) {
        val js =
            """
            (function(){
              try {
                window.dispatchEvent(new CustomEvent('vendiqo-modem-handshake', {
                  detail: { ok: ${if (ok) "true" else "false"} }
                }));
              } catch (e) {}
            })();
            """.trimIndent()
        val handler = mainHandler
        val evaluate = {
            webViewProvider?.invoke()?.evaluateJavascript(js, null)
        }
        if (handler == null) {
            evaluate()
        } else {
            handler.post { evaluate() }
        }
    }
}
