package ch.vendiqo.app

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.webkit.WebViewAssetLoader

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var printerBridge: BluetoothPrinterBridge
    private val insetsBridge =
        AndroidInsetsBridge { resources.displayMetrics.density }

    private lateinit var assetLoader: WebViewAssetLoader

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        assetLoader =
            WebViewAssetLoader.Builder()
                .addPathHandler("/", WebViewAssetLoader.AssetsPathHandler(this))
                .build()

        webView = WebView(this)
        webView.overScrollMode = View.OVER_SCROLL_NEVER
        webView.setBackgroundColor(Color.parseColor("#0f172a"))
        setContentView(webView)
        ViewCompat.requestApplyInsets(webView)

        ViewCompat.setOnApplyWindowInsetsListener(webView) { _, insets ->
            val insetTypes =
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout()
            val bars = insets.getInsets(insetTypes)
            insetsBridge.update(bars.top, bars.bottom, bars.left, bars.right)
            if (::webView.isInitialized) {
                insetsBridge.applyToWebView(webView)
            }
            insets
        }

        webView.webViewClient =
            object : WebViewClient() {
                override fun shouldInterceptRequest(
                    view: WebView,
                    request: WebResourceRequest,
                ) = assetLoader.shouldInterceptRequest(request.url)

                override fun onPageFinished(view: WebView?, url: String?) {
                    super.onPageFinished(view, url)
                    insetsBridge.applyToWebView(webView)
                }
            }
        webView.webChromeClient = WebChromeClient()
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            allowFileAccessFromFileURLs = true
            cacheMode = WebSettings.LOAD_DEFAULT
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            userAgentString = "$userAgentString PiFrontendAndroid"
        }
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        printerBridge = BluetoothPrinterBridge(this)
        webView.addJavascriptInterface(printerBridge, "AndroidPrinter")
        webView.addJavascriptInterface(insetsBridge, "AndroidInsets")

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
        val useDevFrontend = intent.getBooleanExtra("use_dev_frontend", false)
        val loadUrl =
            when {
                intentUrl.startsWith("http://") || intentUrl.startsWith("https://") -> intentUrl
                BuildConfig.DEBUG &&
                    useDevFrontend &&
                    !useBundled &&
                    BuildConfig.DEV_FRONTEND_URL.isNotBlank() ->
                    BuildConfig.DEV_FRONTEND_URL
                else -> BUNDLED_START_URL
            }
        webView.loadUrl(loadUrl)
    }

    override fun onDestroy() {
        if (::webView.isInitialized) {
            webView.destroy()
        }
        super.onDestroy()
    }

    companion object {
        /** Vite bundle lives under assets/public/; file:// cannot load ES modules reliably. */
        private const val BUNDLED_START_URL = "https://appassets.androidplatform.net/public/index.html"
    }
}
