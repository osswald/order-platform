package ch.vendiqo.app

import com.stripe.stripeterminal.external.models.LocaleConfig
import org.junit.Assert.assertSame
import org.junit.Test

class TerminalLocaleConfigTest {
    @Test
    fun forInit_usesCardLanguagePreferenceIfAvailable() {
        assertSame(
            LocaleConfig.CardLanguagePreferenceIfAvailable,
            TerminalLocaleConfig.forInit(),
        )
    }
}
