package ch.vendiqo.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
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
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.webkit.WebViewAssetLoader

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var printerBridge: BluetoothPrinterBridge
    private lateinit var terminalBridge: StripeTerminalBridge

    private val locationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }
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
        terminalBridge = StripeTerminalBridge(this)
        requestTerminalPermissionsIfNeeded()
        webView.addJavascriptInterface(printerBridge, "AndroidPrinter")
        webView.addJavascriptInterface(terminalBridge, "AndroidTerminal")
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

    private fun requestTerminalPermissionsIfNeeded() {
        val needed =
            buildList {
                if (!isGranted(Manifest.permission.ACCESS_FINE_LOCATION)) {
                    add(Manifest.permission.ACCESS_FINE_LOCATION)
                }
                if (!isGranted(Manifest.permission.ACCESS_COARSE_LOCATION)) {
                    add(Manifest.permission.ACCESS_COARSE_LOCATION)
                }
            }
        if (needed.isNotEmpty()) {
            locationPermissionLauncher.launch(needed.toTypedArray())
        }
    }

    private fun isGranted(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED
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
