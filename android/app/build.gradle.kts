import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile
import java.io.File
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val repoRoot = rootProject.projectDir.parentFile
val appVersionFile = repoRoot.resolve("VERSION")
val appVersion = if (appVersionFile.isFile) {
    appVersionFile.readText().trim()
} else {
    "0.0.0-dev"
}
val appVersionCode = appVersion.split(".").let { parts ->
    (parts.getOrNull(0)?.toIntOrNull() ?: 0) * 10000 +
        (parts.getOrNull(1)?.toIntOrNull() ?: 0) * 100 +
        (parts.getOrNull(2)?.replace(Regex("[^0-9].*"), "")?.toIntOrNull() ?: 0)
}

android {
    namespace = "ch.vendiqo.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "ch.vendiqo.app"
        minSdk = 33
        targetSdk = 35
        versionCode = appVersionCode
        versionName = appVersion
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    signingConfigs {
        create("release") {
            val keystorePropsFile = rootProject.file("keystore.properties")
            if (keystorePropsFile.isFile) {
                val keystoreProps = Properties().apply {
                    keystorePropsFile.inputStream().use { load(it) }
                }
                storeFile = rootProject.file(keystoreProps.getProperty("storeFile") ?: "")
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        debug {
            buildConfigField("String", "DEV_FRONTEND_URL", "\"http://localhost:5174\"")
        }
        release {
            isMinifyEnabled = false
            buildConfigField("String", "DEV_FRONTEND_URL", "\"\"")
            val releaseSigning = signingConfigs.getByName("release")
            versionNameSuffix = "0.1"
            if (releaseSigning.storeFile?.exists() == true) {
                signingConfig = releaseSigning
            }
        }
    }
}

tasks.withType<KotlinCompile>().configureEach {
    compilerOptions.jvmTarget.set(JvmTarget.JVM_17)
}

dependencies {
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.webkit:webkit:1.12.1")
    val stripeTerminalVersion = "5.5.1"
    implementation("com.stripe:stripeterminal-taptopay:$stripeTerminalVersion")
    implementation("com.stripe:stripeterminal-core:$stripeTerminalVersion")
}

val frontendDir = rootProject.projectDir.parentFile.resolve("pi/frontend")
val frontendDistDir = frontendDir.resolve("dist")
val assetOutputDir = projectDir.resolve("src/main/assets/public")
val frontendLockFile = frontendDir.resolve("package-lock.json")
val frontendModulesDir = frontendDir.resolve("node_modules")
val resolveNpmScript = rootProject.projectDir.resolve("scripts/resolve-npm.sh")

/** Absolute npm path — Android Studio's Gradle daemon often lacks Homebrew on PATH. */
fun resolveNpmExecutable(): String {
    val process = ProcessBuilder(resolveNpmScript.absolutePath)
        .redirectError(ProcessBuilder.Redirect.PIPE)
        .start()
    val stdout = process.inputStream.bufferedReader().readText().trim()
    val stderr = process.errorStream.bufferedReader().readText().trim()
    val code = process.waitFor()
    if (code != 0 || stdout.isEmpty()) {
        error(stderr.ifEmpty { "Failed to resolve npm (exit $code). See android/scripts/resolve-npm.sh" })
    }
    return stdout
}

fun Exec.configureNpmExec(vararg args: String) {
    val npm = resolveNpmExecutable()
    val npmDir = File(npm).parent
    val path = System.getenv("PATH").orEmpty()
    environment(
        "PATH" to listOfNotNull(npmDir).plus(path).joinToString(File.pathSeparator),
    )
    commandLine(npm, *args)
}

tasks.register<Exec>("installPiFrontend") {
    workingDir = frontendDir
    inputs.file(frontendLockFile)
    outputs.dir(frontendModulesDir)
    configureNpmExec("ci")
}

tasks.register<Exec>("buildPiFrontend") {
    dependsOn("installPiFrontend")
    workingDir = frontendDir
    inputs.dir(frontendDir.resolve("src"))
    inputs.file(frontendDir.resolve("vite.config.ts"))
    inputs.file(frontendDir.resolve("tsconfig.json"))
    inputs.file(frontendLockFile)
    outputs.dir(frontendDistDir)
    val apiBase = (project.findProperty("VITE_API_BASE") as String?)?.trim().orEmpty()
    if (apiBase.isNotEmpty()) {
        environment("VITE_API_BASE" to apiBase)
    }
    configureNpmExec("run", "build", "--", "--mode", "android")
}

tasks.register<Copy>("copyPiFrontendAssets") {
    dependsOn("buildPiFrontend")
    from(frontendDistDir)
    into(assetOutputDir)
}

tasks.named("preBuild") {
    dependsOn("copyPiFrontendAssets")
}
