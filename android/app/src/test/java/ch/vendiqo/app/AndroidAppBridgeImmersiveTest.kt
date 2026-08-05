package ch.vendiqo.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidAppBridgeImmersiveTest {
    @Test
    fun setImmersiveModeWithoutHandlerAppliesImmediately() {
        val applied = mutableListOf<Boolean>()
        val controller = ImmersiveModeController { applied.add(it) }
        val bridge = AndroidAppBridge(immersive = controller, mainHandler = null)

        bridge.setImmersiveMode(true)
        assertTrue(controller.enabled)
        bridge.setImmersiveMode(false)
        assertEquals(listOf(true, false), applied)
    }

    @Test
    fun setImmersiveModeWithoutControllerIsNoOp() {
        val bridge = AndroidAppBridge(immersive = null, mainHandler = null)
        bridge.setImmersiveMode(true)
    }
}
