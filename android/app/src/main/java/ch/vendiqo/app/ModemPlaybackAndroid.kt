package ch.vendiqo.app

import android.content.Context
import android.media.AudioManager
import android.media.MediaPlayer

class AudioManagerVolumeControl(
    private val audioManager: AudioManager,
) : StreamVolumeControl {
    override fun getVolume(): Int = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)

    override fun getMaxVolume(): Int = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)

    override fun setVolume(index: Int) {
        audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, index, 0)
    }
}

/** Plays [resId] from app resources via [MediaPlayer.create]. */
class RawModemSamplePlayer(
    private val context: Context,
    private val resId: Int,
) : ModemSamplePlayer {
    private var mediaPlayer: MediaPlayer? = null
    private var reported = false

    override fun start(onFinished: (ok: Boolean) -> Unit) {
        try {
            val player = MediaPlayer.create(context, resId)
            if (player == null) {
                reportOnce(onFinished, false)
                return
            }
            mediaPlayer = player
            player.setOnCompletionListener {
                reportOnce(onFinished, true)
            }
            player.setOnErrorListener { _, _, _ ->
                reportOnce(onFinished, false)
                true
            }
            player.start()
        } catch (_: Exception) {
            reportOnce(onFinished, false)
        }
    }

    override fun release() {
        val player = mediaPlayer
        mediaPlayer = null
        if (player != null) {
            try {
                player.setOnCompletionListener(null)
                player.setOnErrorListener(null)
                if (player.isPlaying) {
                    player.stop()
                }
            } catch (_: Exception) {
                // Ignore stop errors during teardown.
            }
            try {
                player.release()
            } catch (_: Exception) {
                // Ignore release errors.
            }
        }
    }

    private fun reportOnce(
        onFinished: (Boolean) -> Unit,
        ok: Boolean,
    ) {
        if (reported) return
        reported = true
        onFinished(ok)
    }
}
