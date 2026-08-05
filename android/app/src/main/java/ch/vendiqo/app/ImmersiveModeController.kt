package ch.vendiqo.app

/**
 * Tracks immersive (system-bar hidden) preference and applies it via [apply].
 * JVM-testable without WindowInsetsController.
 */
class ImmersiveModeController(
    private val apply: (Boolean) -> Unit,
) {
    @Volatile
    var enabled: Boolean = false
        private set

    fun setEnabled(enabled: Boolean) {
        this.enabled = enabled
        apply(enabled)
    }
}
