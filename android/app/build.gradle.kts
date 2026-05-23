plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ch.orderplatform.pi"
    compileSdk = 35

    defaultConfig {
        applicationId = "ch.orderplatform.pi"
        minSdk = 31
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
}

val frontendDir = rootProject.projectDir.parentFile.resolve("pi/frontend")
val frontendDistDir = frontendDir.resolve("dist")
val assetOutputDir = projectDir.resolve("src/main/assets/public")

tasks.register<Exec>("installPiFrontend") {
    workingDir = frontendDir
    commandLine("npm", "ci")
}

tasks.register<Exec>("buildPiFrontend") {
    dependsOn("installPiFrontend")
    workingDir = frontendDir
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
