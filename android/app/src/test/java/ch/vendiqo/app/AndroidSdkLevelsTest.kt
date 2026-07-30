package ch.vendiqo.app

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Guards Play target-API compliance: compileSdk / targetSdk must stay ≥ 36.
 * Reads the app module Gradle file (unit-test cwd is typically `android/app`).
 */
class AndroidSdkLevelsTest {
    @Test
    fun compileAndTargetSdkAreAtLeast36() {
        val gradleFile = resolveAppBuildGradle()
        val text = gradleFile.readText()
        val compile = Regex("""compileSdk\s*=\s*(\d+)""").find(text)
            ?: error("compileSdk not found in ${gradleFile.path}")
        val target = Regex("""targetSdk\s*=\s*(\d+)""").find(text)
            ?: error("targetSdk not found in ${gradleFile.path}")
        val compileSdk = compile.groupValues[1].toInt()
        val targetSdk = target.groupValues[1].toInt()
        assertTrue("compileSdk=$compileSdk must be ≥ 36", compileSdk >= 36)
        assertTrue("targetSdk=$targetSdk must be ≥ 36", targetSdk >= 36)
    }

    private fun resolveAppBuildGradle(): File {
        val candidates =
            listOf(
                File("build.gradle.kts"),
                File("app/build.gradle.kts"),
                File("android/app/build.gradle.kts"),
            )
        return candidates.firstOrNull { it.isFile }
            ?: error(
                "Could not find app/build.gradle.kts (cwd=${File(".").absolutePath})",
            )
    }
}
