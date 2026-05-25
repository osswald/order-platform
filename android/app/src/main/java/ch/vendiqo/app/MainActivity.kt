package ch.vendiqo.app

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var printerBridge: BluetoothPrinterBridge

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this)
        setContentView(webView)

        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            cacheMode = WebSettings.LOAD_DEFAULT
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            userAgentString = "$userAgentString PiFrontendAndroid"
        }
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        printerBridge = BluetoothPrinterBridge(this)
        webView.addJavascriptInterface(printerBridge, "AndroidPrinter")

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (webView.canGoBack()) {
                        webView.goBack()
                    } else {
                        isEnabled = false
                        onBackPressedDispatcher.onBackPressed()
                    }
                }
            },
        )

        val intentUrl = intent.getStringExtra("frontend_url")?.trim().orEmpty()
        val useBundled = intent.getBooleanExtra("use_bundled_frontend", false)
        val loadUrl = when {
            intentUrl.startsWith("http://") || intentUrl.startsWith("https://") -> intentUrl
            BuildConfig.DEBUG && !useBundled && BuildConfig.DEV_FRONTEND_URL.isNotBlank() ->
                BuildConfig.DEV_FRONTEND_URL
            else -> "file:///android_asset/public/index.html"
        }
        webView.loadUrl(loadUrl)
    }

    override fun onDestroy() {
        if (::webView.isInitialized) {
            webView.destroy()
        }
        super.onDestroy()
    }
}
