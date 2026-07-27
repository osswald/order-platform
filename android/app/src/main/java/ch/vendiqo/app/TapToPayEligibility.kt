package ch.vendiqo.app

import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate
import java.time.format.DateTimeParseException

data class EligibilityCheck(
    val id: String,
    val ok: Boolean,
    val detail: String? = null,
)

/**
 * Pure Tap to Pay eligibility probes for Admin diagnostics.
 * Overall bridge `code` / `supported` semantics stay in [StripeTerminalBridge].
 */
object TapToPayEligibility {
    const val ID_LOCATION = "location"
    const val ID_ANDROID_VERSION = "android_version"
    const val ID_NFC = "nfc"
    const val ID_HARDWARE_KEYSTORE = "hardware_keystore"
    const val ID_GMS = "gms"
    const val ID_SECURITY_PATCH = "security_patch"
    const val ID_DEVELOPER_OPTIONS = "developer_options"
    const val ID_INTERNET = "internet"
    const val ID_SDK_SUPPORT = "sdk_support"

    const val MIN_SDK_INT = 33
    const val MIN_KEYSTORE_VERSION = 100
    const val MAX_SECURITY_PATCH_AGE_MONTHS = 12L

    fun checkLocation(granted: Boolean): EligibilityCheck =
        EligibilityCheck(
            id = ID_LOCATION,
            ok = granted,
            detail = if (granted) null else "Standortberechtigung fehlt",
        )

    fun checkAndroidVersion(sdkInt: Int): EligibilityCheck =
        EligibilityCheck(
            id = ID_ANDROID_VERSION,
            ok = sdkInt >= MIN_SDK_INT,
            detail = if (sdkInt >= MIN_SDK_INT) null else "Android $MIN_SDK_INT+ erforderlich (aktuell $sdkInt)",
        )

    fun checkNfc(hasNfc: Boolean): EligibilityCheck =
        EligibilityCheck(
            id = ID_NFC,
            ok = hasNfc,
            detail = if (hasNfc) null else "Kein NFC",
        )

    fun checkHardwareKeystore(hasFeature: Boolean, version: Int?): EligibilityCheck {
        val ok =
            when {
                !hasFeature -> false
                version == null -> true
                else -> version >= MIN_KEYSTORE_VERSION
            }
        val detail =
            when {
                ok -> null
                !hasFeature -> "Kein Hardware-Keystore"
                else -> "Hardware-Keystore Version $MIN_KEYSTORE_VERSION+ erforderlich (aktuell $version)"
            }
        return EligibilityCheck(id = ID_HARDWARE_KEYSTORE, ok = ok, detail = detail)
    }

    fun checkGms(hasPlayStore: Boolean, hasGms: Boolean): EligibilityCheck {
        val ok = hasPlayStore || hasGms
        return EligibilityCheck(
            id = ID_GMS,
            ok = ok,
            detail = if (ok) null else "Google Play / GMS fehlt",
        )
    }

    fun checkSecurityPatch(securityPatch: String, now: LocalDate = LocalDate.now()): EligibilityCheck {
        val patchDate =
            try {
                LocalDate.parse(securityPatch.trim())
            } catch (_: DateTimeParseException) {
                null
            }
        if (patchDate == null) {
            return EligibilityCheck(
                id = ID_SECURITY_PATCH,
                ok = false,
                detail = "Sicherheitsupdate unbekannt",
            )
        }
        val oldestAllowed = now.minusMonths(MAX_SECURITY_PATCH_AGE_MONTHS)
        val ok = !patchDate.isBefore(oldestAllowed) && !patchDate.isAfter(now)
        return EligibilityCheck(
            id = ID_SECURITY_PATCH,
            ok = ok,
            detail =
                if (ok) {
                    null
                } else {
                    "Sicherheitsupdate älter als $MAX_SECURITY_PATCH_AGE_MONTHS Monate ($securityPatch)"
                },
        )
    }

    fun checkDeveloperOptions(enabled: Boolean, isDebugBuild: Boolean): EligibilityCheck {
        if (isDebugBuild) {
            return EligibilityCheck(
                id = ID_DEVELOPER_OPTIONS,
                ok = true,
                detail = if (enabled) "Debug-Build (simuliert)" else null,
            )
        }
        return EligibilityCheck(
            id = ID_DEVELOPER_OPTIONS,
            ok = !enabled,
            detail = if (enabled) "Entwickleroptionen aktiv" else null,
        )
    }

    fun checkInternet(connected: Boolean): EligibilityCheck =
        EligibilityCheck(
            id = ID_INTERNET,
            ok = connected,
            detail = if (connected) null else "Keine Netzwerkverbindung",
        )

    fun checkSdkSupport(supported: Boolean, detail: String?): EligibilityCheck =
        EligibilityCheck(
            id = ID_SDK_SUPPORT,
            ok = supported,
            detail = if (supported) null else (detail ?: "Stripe SDK: nicht unterstützt"),
        )

    fun checkSdkSupportSkipped(detail: String): EligibilityCheck =
        EligibilityCheck(id = ID_SDK_SUPPORT, ok = false, detail = detail)

    fun composeChecks(
        locationOk: Boolean,
        sdkInt: Int,
        hasNfc: Boolean,
        keystoreHasFeature: Boolean,
        keystoreVersion: Int?,
        hasPlayStore: Boolean,
        hasGms: Boolean,
        securityPatch: String,
        now: LocalDate = LocalDate.now(),
        developerOptionsEnabled: Boolean,
        isDebugBuild: Boolean,
        internetOk: Boolean,
        sdkSupport: EligibilityCheck,
    ): List<EligibilityCheck> =
        listOf(
            checkLocation(locationOk),
            checkAndroidVersion(sdkInt),
            checkNfc(hasNfc),
            checkHardwareKeystore(keystoreHasFeature, keystoreVersion),
            checkGms(hasPlayStore, hasGms),
            checkSecurityPatch(securityPatch, now),
            checkDeveloperOptions(developerOptionsEnabled, isDebugBuild),
            checkInternet(internetOk),
            sdkSupport,
        )

    fun toJsonArray(checks: List<EligibilityCheck>): JSONArray {
        val array = JSONArray()
        for (check in checks) {
            val obj = JSONObject().put("id", check.id).put("ok", check.ok)
            if (check.detail != null) obj.put("detail", check.detail)
            array.put(obj)
        }
        return array
    }
}
