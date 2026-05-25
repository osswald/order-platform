import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ch.vendiqo.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "ch.vendiqo.app"
        minSdk = 31
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
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
}

val frontendDir = rootProject.projectDir.parentFile.resolve("pi/frontend")
val frontendDistDir = frontendDir.resolve("dist")
val assetOutputDir = projectDir.resolve("src/main/assets/public")
val frontendLockFile = frontendDir.resolve("package-lock.json")
val frontendModulesDir = frontendDir.resolve("node_modules")

tasks.register<Exec>("installPiFrontend") {
    workingDir = frontendDir
    inputs.file(frontendLockFile)
    outputs.dir(frontendModulesDir)
    commandLine("npm", "ci")
}

tasks.register<Exec>("buildPiFrontend") {
    dependsOn("installPiFrontend")
    workingDir = frontendDir
    inputs.dir(frontendDir.resolve("src"))
    inputs.file(frontendDir.resolve("vite.config.js"))
    inputs.file(frontendLockFile)
    outputs.dir(frontendDistDir)
    val apiBase = (project.findProperty("VITE_API_BASE") as String?)?.trim().orEmpty()
    if (apiBase.isNotEmpty()) {
        environment("VITE_API_BASE" to apiBase)
    }
    commandLine("npm", "run", "build", "--", "--mode", "android")
}

tasks.register<Copy>("copyPiFrontendAssets") {
    dependsOn("buildPiFrontend")
    from(frontendDistDir)
    into(assetOutputDir)
}

tasks.named("preBuild") {
    dependsOn("copyPiFrontendAssets")
}
