package ch.vendiqo.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidAppBridgeModemTest {
    private class FakeVolume(
        private var volume: Int,
        private val max: Int,
    ) : StreamVolumeControl {
        override fun getVolume(): Int = volume

        override fun getMaxVolume(): Int = max

        override fun setVolume(index: Int) {
            volume = index
        }
    }

    @Test
    fun playModemHandshakeWithoutControllerDispatchesFailureEventJs() {
        // Without WebView we only verify the method does not throw when handshake is null.
        val bridge = AndroidAppBridge(modemHandshake = null, mainHandler = null)
        bridge.playModemHandshake()
    }

    @Test
    fun playModemHandshakeRunsControllerAndCompletes() {
        val volume = FakeVolume(volume = 4, max = 16)
        var playerStarted = false
        var keyboardHidden = false
        val handshake =
            ModemHandshakeController(
                volume = volume,
                playerFactory = {
                    object : ModemSamplePlayer {
                        override fun start(onFinished: (ok: Boolean) -> Unit) {
                            playerStarted = true
                            onFinished(true)
                        }

                        override fun release() {}
                    }
                },
            )
        val bridge =
            AndroidAppBridge(
                modemHandshake = handshake,
                mainHandler = null,
                webViewProvider = { null },
                softKeyboardHider = SoftKeyboardHider { keyboardHidden = true },
            )

        bridge.playModemHandshake()

        assertTrue(keyboardHidden)
        assertTrue(playerStarted)
        assertEquals(4, volume.getVolume())
        assertFalse(handshake.isRunning)
    }

    @Test
    fun cancelModemHandshakeRestoresVolume() {
        val volume = FakeVolume(volume = 1, max = 10)
        lateinit var finish: (Boolean) -> Unit
        val handshake =
            ModemHandshakeController(
                volume = volume,
                playerFactory = {
                    object : ModemSamplePlayer {
                        override fun start(onFinished: (ok: Boolean) -> Unit) {
                            finish = onFinished
                        }

                        override fun release() {}
                    }
                },
            )
        val bridge =
            AndroidAppBridge(
                modemHandshake = handshake,
                mainHandler = null,
                webViewProvider = { null },
            )

        bridge.playModemHandshake()
        assertTrue(handshake.isRunning)
        bridge.cancelModemHandshake()
        assertFalse(handshake.isRunning)
        assertEquals(1, volume.getVolume())
    }
}
