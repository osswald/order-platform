package ch.vendiqo.app

/** Media stream volume control used by the modem handshake (JVM-testable). */
interface StreamVolumeControl {
    fun getVolume(): Int

    fun getMaxVolume(): Int

    fun setVolume(index: Int)
}

/** Plays the bundled modem sample once. */
interface ModemSamplePlayer {
    /** Start playback; invoke [onFinished] exactly once. */
    fun start(onFinished: (ok: Boolean) -> Unit)

    fun release()
}

/**
 * Saves media volume, raises to ~[targetPercent]%, plays the modem sample, then restores volume.
 * Soft-fails (restores volume, reports ok=false) when playback cannot start.
 */
class ModemHandshakeController(
    private val volume: StreamVolumeControl,
    private val playerFactory: () -> ModemSamplePlayer,
    private val targetPercent: Int = 75,
) {
    @Volatile
    var isRunning: Boolean = false
        private set

    private var savedVolume: Int? = null
    private var player: ModemSamplePlayer? = null
    private var finishedCallback: ((Boolean) -> Unit)? = null
    private val lock = Any()

    fun start(onFinished: (ok: Boolean) -> Unit) {
        synchronized(lock) {
            if (isRunning) {
                onFinished(false)
                return
            }
            isRunning = true
            finishedCallback = onFinished
            try {
                val max = volume.getMaxVolume().coerceAtLeast(1)
                savedVolume = volume.getVolume()
                val target = ((max * targetPercent) / 100).coerceIn(0, max)
                volume.setVolume(target)
                val p = playerFactory()
                player = p
                p.start { ok -> finish(ok) }
            } catch (_: Exception) {
                finish(false)
            }
        }
    }

    /** Abort playback (e.g. Activity destroy): restore volume and signal failure. */
    fun cancel() {
        finish(false)
    }

    private fun finish(ok: Boolean) {
        val callback: ((Boolean) -> Unit)?
        synchronized(lock) {
            if (!isRunning && savedVolume == null && player == null) {
                return
            }
            val saved = savedVolume
            savedVolume = null
            val p = player
            player = null
            isRunning = false
            callback = finishedCallback
            finishedCallback = null
            if (saved != null) {
                try {
                    volume.setVolume(saved)
                } catch (_: Exception) {
                    // Best-effort restore.
                }
            }
            if (p != null) {
                try {
                    p.release()
                } catch (_: Exception) {
                    // Ignore release errors.
                }
            }
        }
        callback?.invoke(ok)
    }
}
