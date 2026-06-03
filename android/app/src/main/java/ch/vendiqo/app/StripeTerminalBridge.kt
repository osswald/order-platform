package ch.vendiqo.app

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.webkit.JavascriptInterface
import com.stripe.stripeterminal.Terminal
import com.stripe.stripeterminal.external.callable.Callback
import com.stripe.stripeterminal.external.callable.ConnectionTokenCallback
import com.stripe.stripeterminal.external.callable.ConnectionTokenProvider
import com.stripe.stripeterminal.external.callable.DiscoveryListener
import com.stripe.stripeterminal.external.callable.PaymentIntentCallback
import com.stripe.stripeterminal.external.callable.ReaderCallback
import com.stripe.stripeterminal.external.callable.TapToPayReaderListener
import com.stripe.stripeterminal.external.callable.TerminalListener
import com.stripe.stripeterminal.external.models.CollectPaymentIntentConfiguration
import com.stripe.stripeterminal.external.models.ConfirmPaymentIntentConfiguration
import com.stripe.stripeterminal.external.models.ConnectionConfiguration
import com.stripe.stripeterminal.external.models.ConnectionStatus
import com.stripe.stripeterminal.external.models.ConnectionTokenException
import com.stripe.stripeterminal.external.models.DiscoveryConfiguration
import com.stripe.stripeterminal.external.models.PaymentIntent
import com.stripe.stripeterminal.external.models.Reader
import com.stripe.stripeterminal.external.models.TerminalException
import com.stripe.stripeterminal.log.LogLevel
import org.json.JSONObject
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

class StripeTerminalBridge(private val activity: Activity) {
    private val executor = Executors.newSingleThreadExecutor()
    private val tokenProvider = EphemeralConnectionTokenProvider()

    @JavascriptInterface
    fun isAvailable(): String = ok("available" to Terminal.isInitialized())

    @JavascriptInterface
    fun collectPayment(connectionTokenSecret: String, paymentIntentClientSecret: String): String {
        if (!hasLocationPermission()) {
            return error("Standortberechtigung für Kartenzahlung erforderlich.")
        }
        val latch = CountDownLatch(1)
        val out = AtomicReference(error("Kartenzahlung fehlgeschlagen."))
        executor.execute {
            try {
                ensureTerminalInitialized()
                ensureTapToPayConnected(connectionTokenSecret)
                out.set(processPayment(paymentIntentClientSecret))
            } catch (e: Exception) {
                out.set(error(e.message ?: "Kartenzahlung fehlgeschlagen."))
            } finally {
                latch.countDown()
            }
        }
        latch.await(120, TimeUnit.SECONDS)
        return out.get()
    }

    private fun hasLocationPermission(): Boolean {
        val fine =
            activity.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED
        val coarse =
            activity.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED
        return fine || coarse
    }

    private fun ensureTerminalInitialized() {
        if (Terminal.isInitialized()) return
        val latch = CountDownLatch(1)
        val err = AtomicReference<Exception?>(null)
        activity.runOnUiThread {
            try {
                Terminal.init(
                    activity.applicationContext,
                    LogLevel.VERBOSE,
                    tokenProvider,
                    TerminalListenerAdapter(),
                    null,
                )
            } catch (e: TerminalException) {
                err.set(e)
            } finally {
                latch.countDown()
            }
        }
        latch.await(10, TimeUnit.SECONDS)
        err.get()?.let { throw it }
        if (!Terminal.isInitialized()) {
            throw IllegalStateException("Stripe Terminal konnte nicht initialisiert werden.")
        }
    }

    private fun ensureTapToPayConnected(connectionTokenSecret: String) {
        tokenProvider.secret = connectionTokenSecret
        val terminal = Terminal.getInstance()
        if (terminal.connectionStatus == ConnectionStatus.CONNECTED && terminal.connectedReader != null) {
            return
        }
        val reader = discoverTapToPayReader()
        connectReader(reader)
    }

    private fun discoverTapToPayReader(): Reader {
        val terminal = Terminal.getInstance()
        val readers = mutableListOf<Reader>()
        val latch = CountDownLatch(1)
        val discoveryError = AtomicReference<Exception?>(null)
        val simulated = BuildConfig.DEBUG
        val config = DiscoveryConfiguration.TapToPayDiscoveryConfiguration(isSimulated = simulated)
        val discoveryTask =
            terminal.discoverReaders(
                config,
                object : DiscoveryListener {
                    override fun onUpdateDiscoveredReaders(discoveredReaders: List<Reader>) {
                        readers.clear()
                        readers.addAll(discoveredReaders)
                    }
                },
                object : Callback {
                    override fun onSuccess() {
                        latch.countDown()
                    }

                    override fun onFailure(e: TerminalException) {
                        discoveryError.set(e)
                        latch.countDown()
                    }
                },
            )
        latch.await(30, TimeUnit.SECONDS)
        discoveryTask?.cancel(object : Callback {
            override fun onSuccess() {}
            override fun onFailure(e: TerminalException) {}
        })
        discoveryError.get()?.let { throw it }
        return readers.firstOrNull()
            ?: throw IllegalStateException("Kein Tap-to-Pay-Lesegerät gefunden.")
    }

    private fun connectReader(reader: Reader) {
        val terminal = Terminal.getInstance()
        val latch = CountDownLatch(1)
        val connectError = AtomicReference<Exception?>(null)
        val locationId = reader.location?.id
            ?: throw IllegalStateException("Tap-to-Pay-Lesegerät ohne Standort-ID.")
        val config =
            ConnectionConfiguration.TapToPayConnectionConfiguration(
                locationId = locationId,
                autoReconnectOnUnexpectedDisconnect = true,
                tapToPayReaderListener = object : TapToPayReaderListener {},
            )
        terminal.connectReader(
            reader,
            config,
            object : ReaderCallback {
                override fun onSuccess(reader: Reader) {
                    latch.countDown()
                }

                override fun onFailure(e: TerminalException) {
                    connectError.set(e)
                    latch.countDown()
                }
            },
        )
        latch.await(30, TimeUnit.SECONDS)
        connectError.get()?.let { throw it }
    }

    private fun processPayment(clientSecret: String): String {
        val intent = retrievePaymentIntent(clientSecret)
        val latch = CountDownLatch(1)
        val result = AtomicReference<String>(error("Kartenzahlung fehlgeschlagen."))
        val collectConfig = CollectPaymentIntentConfiguration.Builder().build()
        val confirmConfig = ConfirmPaymentIntentConfiguration.Builder().build()
        Terminal.getInstance().processPaymentIntent(
            intent,
            collectConfig,
            confirmConfig,
            object : PaymentIntentCallback {
                override fun onSuccess(paymentIntent: PaymentIntent) {
                    result.set(
                        ok(
                            "payment_intent_id" to (paymentIntent.id ?: ""),
                        ),
                    )
                    latch.countDown()
                }

                override fun onFailure(e: TerminalException) {
                    result.set(error(e.errorMessage ?: e.message ?: "Kartenzahlung fehlgeschlagen."))
                    latch.countDown()
                }
            },
        )
        latch.await(120, TimeUnit.SECONDS)
        return result.get()
    }

    private fun retrievePaymentIntent(clientSecret: String): PaymentIntent {
        val latch = CountDownLatch(1)
        val intentRef = AtomicReference<PaymentIntent?>(null)
        val retrieveError = AtomicReference<Exception?>(null)
        Terminal.getInstance().retrievePaymentIntent(
            clientSecret,
            object : PaymentIntentCallback {
                override fun onSuccess(paymentIntent: PaymentIntent) {
                    intentRef.set(paymentIntent)
                    latch.countDown()
                }

                override fun onFailure(e: TerminalException) {
                    retrieveError.set(e)
                    latch.countDown()
                }
            },
        )
        latch.await(30, TimeUnit.SECONDS)
        retrieveError.get()?.let { throw it }
        return intentRef.get() ?: throw IllegalStateException("PaymentIntent konnte nicht geladen werden.")
    }

    private fun ok(vararg pairs: Pair<String, Any?>): String {
        val json = JSONObject()
        json.put("ok", true)
        for ((key, value) in pairs) json.put(key, value)
        return json.toString()
    }

    private fun error(message: String): String {
        return JSONObject()
            .put("ok", false)
            .put("error", message)
            .toString()
    }

    private class EphemeralConnectionTokenProvider : ConnectionTokenProvider {
        @Volatile
        var secret: String? = null

        override fun fetchConnectionToken(callback: ConnectionTokenCallback) {
            val token = secret?.trim().orEmpty()
            if (token.isEmpty()) {
                callback.onFailure(ConnectionTokenException("Kein Connection Token."))
            } else {
                callback.onSuccess(token)
            }
        }
    }

    private class TerminalListenerAdapter : TerminalListener
}
