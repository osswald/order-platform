package ch.vendiqo.app

import android.annotation.SuppressLint
import android.graphics.Color
import android.media.AudioManager
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
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.webkit.WebViewAssetLoader

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private lateinit var printerBridge: BluetoothPrinterBridge
    private lateinit var immersiveController: ImmersiveModeController
    private lateinit var modemHandshake: ModemHandshakeController
    private lateinit var appBridge: AndroidAppBridge

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

        val insetsController = WindowCompat.getInsetsController(window, webView)
        immersiveController =
            ImmersiveModeController { enabled ->
                insetsController.systemBarsBehavior =
                    WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                if (enabled) {
                    insetsController.hide(WindowInsetsCompat.Type.systemBars())
                } else {
                    insetsController.show(WindowInsetsCompat.Type.systemBars())
                }
            }

        ViewCompat.setOnApplyWindowInsetsListener(webView) { _, insets ->
            val insetTypes =
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout()
            val bars = insets.getInsets(insetTypes)
            val ime = insets.getInsets(WindowInsetsCompat.Type.ime())
            insetsBridge.update(bars.top, bars.bottom, bars.left, bars.right)
            // Keep IME separate from --safe-bottom so only text-input sheets lift.
            insetsBridge.updateIme(ime.bottom)
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
                ): android.webkit.WebResourceResponse? {
                    // Only intercept bundled asset URLs. Pi HTTP (screensaver images, API)
                    // must hit the network — returning a loader miss 404s those requests.
                    val host = request.url.host
                    if (host != "appassets.androidplatform.net") return null
                    return assetLoader.shouldInterceptRequest(request.url)
                }

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
        val terminalBridge = AndroidTerminalStub()
        val networkBridge = AndroidNetworkBridge()
        val audioManager = getSystemService(AUDIO_SERVICE) as AudioManager
        modemHandshake =
            ModemHandshakeController(
                volume = AudioManagerVolumeControl(audioManager),
                playerFactory = { RawModemSamplePlayer(this, R.raw.modem56k) },
            )
        appBridge =
            AndroidAppBridge(
                immersive = immersiveController,
                mainHandler = android.os.Handler(mainLooper),
                modemHandshake = modemHandshake,
                webViewProvider = { if (::webView.isInitialized) webView else null },
                softKeyboardHider = softKeyboardHiderForActivity(this),
            )
        webView.addJavascriptInterface(printerBridge, "AndroidPrinter")
        webView.addJavascriptInterface(terminalBridge, "AndroidTerminal")
        webView.addJavascriptInterface(appBridge, "AndroidApp")
        webView.addJavascriptInterface(insetsBridge, "AndroidInsets")
        webView.addJavascriptInterface(networkBridge, "AndroidNetwork")

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
        if (::appBridge.isInitialized) {
            appBridge.cancelModemHandshake()
        }
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
