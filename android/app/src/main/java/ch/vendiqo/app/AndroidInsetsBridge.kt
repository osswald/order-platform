package ch.vendiqo.app

import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject

/**
 * Exposes system bar inset sizes to the WebView as CSS px.
 * WindowInsets are in view pixels; WebView CSS px match density-independent pixels (divide by density).
 */
class AndroidInsetsBridge(
    private val density: () -> Float,
) {
    @Volatile
    var topPx: Int = 0

    @Volatile
    var bottomPx: Int = 0

    @Volatile
    var leftPx: Int = 0

    @Volatile
    var rightPx: Int = 0

    fun update(top: Int, bottom: Int, left: Int, right: Int) {
        val d = density().coerceAtLeast(1f)
        topPx = toCssPx(top, d)
        bottomPx = toCssPx(bottom, d)
        leftPx = toCssPx(left, d)
        rightPx = toCssPx(right, d)
    }

    @JavascriptInterface
    fun getSystemBarInsetsJson(): String =
        JSONObject()
            .put("top", topPx)
            .put("bottom", bottomPx)
            .put("left", leftPx)
            .put("right", rightPx)
            .toString()

    fun applyToWebView(webView: WebView) {
        val js =
            """
            (function(){
              try {
                var o = JSON.parse(AndroidInsets.getSystemBarInsetsJson());
                var r = document.documentElement;
                r.style.setProperty('--safe-top', o.top + 'px');
                r.style.setProperty('--safe-bottom', o.bottom + 'px');
                r.style.setProperty('--safe-left', o.left + 'px');
                r.style.setProperty('--safe-right', o.right + 'px');
              } catch (e) {}
            })();
            """.trimIndent()
        webView.evaluateJavascript(js, null)
    }

    private fun toCssPx(px: Int, density: Float): Int =
        if (px <= 0) 0 else (px / density + 0.5f).toInt()
}
