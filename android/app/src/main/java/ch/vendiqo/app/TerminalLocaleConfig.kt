package ch.vendiqo.app

import com.stripe.stripeterminal.external.models.LocaleConfig

/**
 * Locale strategy for [com.stripe.stripeterminal.Terminal.init].
 * Prefers the cardholder language when available, else the device/app locale
 * (avoids English-only Tap to Pay attestation defaults from Terminal 5.6.0+).
 */
object TerminalLocaleConfig {
    fun forInit(): LocaleConfig = LocaleConfig.CardLanguagePreferenceIfAvailable
}
