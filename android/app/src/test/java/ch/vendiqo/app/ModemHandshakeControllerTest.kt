package ch.vendiqo.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ModemHandshakeControllerTest {
    private class FakeVolume(
        private var volume: Int,
        private val max: Int,
    ) : StreamVolumeControl {
        val history = mutableListOf<Int>()

        override fun getVolume(): Int = volume

        override fun getMaxVolume(): Int = max

        override fun setVolume(index: Int) {
            volume = index
            history.add(index)
        }
    }

    private class FakePlayer(
        private val succeed: Boolean,
        private val autoFinish: Boolean = true,
    ) : ModemSamplePlayer {
        var started = false
        var released = false
        private var onFinished: ((Boolean) -> Unit)? = null

        override fun start(onFinished: (ok: Boolean) -> Unit) {
            started = true
            this.onFinished = onFinished
            if (autoFinish) {
                onFinished(succeed)
            }
        }

        fun complete(ok: Boolean) {
            onFinished?.invoke(ok)
        }

        override fun release() {
            released = true
        }
    }

    @Test
    fun successfulPlaybackRaisesThenRestoresVolume() {
        val volume = FakeVolume(volume = 4, max = 16)
        lateinit var player: FakePlayer
        val controller =
            ModemHandshakeController(
                volume = volume,
                playerFactory = {
                    player = FakePlayer(succeed = true, autoFinish = false)
                    player
                },
            )
        var finishedOk: Boolean? = null

        controller.start { finishedOk = it }
        assertEquals(12, volume.history.first()) // 75% of 16
        assertTrue(player.started)

        player.complete(true)
        assertEquals(true, finishedOk)
        assertEquals(4, volume.getVolume())
        assertTrue(player.released)
        assertFalse(controller.isRunning)
    }

    @Test
    fun softFailWhenPlayerCannotStartRestoresVolume() {
        val volume = FakeVolume(volume = 2, max = 10)
        val controller =
            ModemHandshakeController(
                volume = volume,
                playerFactory = {
                    object : ModemSamplePlayer {
                        override fun start(onFinished: (ok: Boolean) -> Unit) {
                            onFinished(false)
                        }

                        override fun release() {}
                    }
                },
            )
        var finishedOk: Boolean? = null

        controller.start { finishedOk = it }

        assertEquals(false, finishedOk)
        assertEquals(2, volume.getVolume())
        assertEquals(listOf(7, 2), volume.history) // 75% of 10 = 7, then restore
    }

    @Test
    fun playerFactoryThrowSoftFailsAndRestores() {
        val volume = FakeVolume(volume = 5, max = 20)
        val controller =
            ModemHandshakeController(
                volume = volume,
                playerFactory = { error("missing resource") },
            )
        var finishedOk: Boolean? = null

        controller.start { finishedOk = it }

        assertEquals(false, finishedOk)
        assertEquals(5, volume.getVolume())
    }

    @Test
    fun cancelRestoresVolumeAndReleasesPlayer() {
        val volume = FakeVolume(volume = 3, max = 8)
        lateinit var player: FakePlayer
        val controller =
            ModemHandshakeController(
                volume = volume,
                playerFactory = {
                    player = FakePlayer(succeed = true, autoFinish = false)
                    player
                },
            )
        var finishedOk: Boolean? = null

        controller.start { finishedOk = it }
        controller.cancel()

        assertEquals(false, finishedOk)
        assertEquals(3, volume.getVolume())
        assertTrue(player.released)
        assertFalse(controller.isRunning)
    }
}
