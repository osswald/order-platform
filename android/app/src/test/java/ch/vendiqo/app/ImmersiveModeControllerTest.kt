package ch.vendiqo.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ImmersiveModeControllerTest {
    @Test
    fun setEnabledTracksStateAndInvokesApply() {
        val applied = mutableListOf<Boolean>()
        val controller = ImmersiveModeController { applied.add(it) }

        assertFalse(controller.enabled)
        controller.setEnabled(true)
        assertTrue(controller.enabled)
        controller.setEnabled(false)
        assertFalse(controller.enabled)

        assertEquals(listOf(true, false), applied)
    }

    @Test
    fun setEnabledCanBeCalledRepeatedly() {
        val applied = mutableListOf<Boolean>()
        val controller = ImmersiveModeController { applied.add(it) }
        controller.setEnabled(true)
        controller.setEnabled(true)
        assertEquals(listOf(true, true), applied)
        assertTrue(controller.enabled)
    }
}
