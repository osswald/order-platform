package ch.vendiqo.app

import android.webkit.JavascriptInterface
import org.json.JSONObject

/**
 * No-op bridge for cached PWAs that still call `window.AndroidTerminal`.
 * Card payments use SumUp Cloud via the web stack; Tap to Pay is no longer supported.
 */
class AndroidTerminalStub {
    @JavascriptInterface
    fun isAvailable(): String =
        JSONObject()
            .put("ok", true)
            .put("available", false)
            .toString()

    @JavascriptInterface
    fun supportsTapToPay(): String =
        JSONObject()
            .put("ok", false)
            .put("supported", false)
            .put("code", "unsupported")
            .put("error", "Kartenzahlung über Stripe Tap to Pay wird nicht mehr unterstützt.")
            .toString()

    @JavascriptInterface
    fun collectPayment(_connectionToken: String, _clientSecret: String): String =
        JSONObject()
            .put("ok", false)
            .put("error", "Kartenzahlung über Stripe Tap to Pay wird nicht mehr unterstützt.")
            .toString()
}
