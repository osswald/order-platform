package ch.vendiqo.app

import android.webkit.JavascriptInterface
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.nio.charset.Charset

/**
 * Native HTTP helpers for the bundled WebView.
 *
 * Cross-origin [fetch] from https://appassets.androidplatform.net can fail in
 * System WebView even when the server sends CORS headers. Connectivity probes
 * use this bridge so Demo / connection-setup do not depend on WebView CORS.
 */
class AndroidNetworkBridge {
    @JavascriptInterface
    fun probeHealth(baseUrl: String): String {
        val base = baseUrl.trim().trimEnd('/')
        if (base.isEmpty()) {
            return error("network", "Empty API base URL.")
        }
        val healthUrl =
            try {
                val uri = URI(base)
                if (uri.scheme != "http" && uri.scheme != "https") {
                    return error("network", "URL must be http or https.")
                }
                if (uri.host.isNullOrBlank()) {
                    return error("network", "URL host is missing.")
                }
                URL("$base/health")
            } catch (e: Exception) {
                return error("network", e.message ?: "Invalid URL.")
            }

        var connection: HttpURLConnection? = null
        return try {
            connection =
                (healthUrl.openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
                    instanceFollowRedirects = true
                    useCaches = false
                    setRequestProperty("Accept", "application/json")
                }
            val code = connection.responseCode
            val stream =
                if (code in 200..299) {
                    connection.inputStream
                } else {
                    connection.errorStream ?: connection.inputStream
                }
            val body =
                stream?.bufferedReader(Charset.forName("UTF-8"))?.use { it.readText() }.orEmpty()
            if (code !in 200..299) {
                return error("http", "HTTP $code")
            }
            if (!body.contains("\"status\"") || !body.contains("\"ok\"")) {
                return error("http", "Health response was not JSON status=ok.")
            }
            JSONObject()
                .put("ok", true)
                .put("status", "ok")
                .put("httpStatus", code)
                .toString()
        } catch (e: Exception) {
            error("network", e.message ?: "Network error.")
        } finally {
            connection?.disconnect()
        }
    }

    private fun error(reason: String, message: String): String =
        JSONObject()
            .put("ok", false)
            .put("reason", reason)
            .put("message", message)
            .toString()

    companion object {
        private const val CONNECT_TIMEOUT_MS = 8_000
        private const val READ_TIMEOUT_MS = 8_000
    }
}
