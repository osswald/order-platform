package ch.vendiqo.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class TapToPayEligibilityTest {
    @Test
    fun androidVersion_passesAt33AndAbove() {
        assertTrue(TapToPayEligibility.checkAndroidVersion(33).ok)
        assertTrue(TapToPayEligibility.checkAndroidVersion(35).ok)
        assertFalse(TapToPayEligibility.checkAndroidVersion(32).ok)
        assertEquals("android_version", TapToPayEligibility.checkAndroidVersion(32).id)
    }

    @Test
    fun nfc_requiresFeature() {
        assertTrue(TapToPayEligibility.checkNfc(true).ok)
        val fail = TapToPayEligibility.checkNfc(false)
        assertFalse(fail.ok)
        assertEquals("nfc", fail.id)
        assertEquals("Kein NFC", fail.detail)
    }

    @Test
    fun hardwareKeystore_requiresFeatureAndVersion100() {
        assertTrue(TapToPayEligibility.checkHardwareKeystore(hasFeature = true, version = 100).ok)
        assertTrue(TapToPayEligibility.checkHardwareKeystore(hasFeature = true, version = 200).ok)
        assertFalse(TapToPayEligibility.checkHardwareKeystore(hasFeature = false, version = null).ok)
        assertFalse(TapToPayEligibility.checkHardwareKeystore(hasFeature = true, version = 99).ok)
        // Feature present without a reported version still passes (best-effort).
        assertTrue(TapToPayEligibility.checkHardwareKeystore(hasFeature = true, version = null).ok)
    }

    @Test
    fun gms_passesWhenPlayOrGmsPresent() {
        assertTrue(TapToPayEligibility.checkGms(hasPlayStore = true, hasGms = false).ok)
        assertTrue(TapToPayEligibility.checkGms(hasPlayStore = false, hasGms = true).ok)
        val fail = TapToPayEligibility.checkGms(hasPlayStore = false, hasGms = false)
        assertFalse(fail.ok)
        assertEquals("gms", fail.id)
    }

    @Test
    fun securityPatch_withinTwelveMonths() {
        val now = LocalDate.of(2026, 7, 27)
        assertTrue(
            TapToPayEligibility.checkSecurityPatch("2026-01-05", now).ok,
        )
        assertTrue(
            TapToPayEligibility.checkSecurityPatch("2025-07-27", now).ok,
        )
        val stale = TapToPayEligibility.checkSecurityPatch("2025-07-26", now)
        assertFalse(stale.ok)
        assertEquals("security_patch", stale.id)
        assertFalse(TapToPayEligibility.checkSecurityPatch("", now).ok)
        assertFalse(TapToPayEligibility.checkSecurityPatch("not-a-date", now).ok)
    }

    @Test
    fun developerOptions_releaseFailsWhenEnabled_debugAlwaysPasses() {
        assertTrue(TapToPayEligibility.checkDeveloperOptions(enabled = false, isDebugBuild = false).ok)
        assertFalse(TapToPayEligibility.checkDeveloperOptions(enabled = true, isDebugBuild = false).ok)
        val debugEnabled = TapToPayEligibility.checkDeveloperOptions(enabled = true, isDebugBuild = true)
        assertTrue(debugEnabled.ok)
        assertEquals("developer_options", debugEnabled.id)
    }

    @Test
    fun internet_and_location() {
        assertTrue(TapToPayEligibility.checkInternet(true).ok)
        assertFalse(TapToPayEligibility.checkInternet(false).ok)
        assertTrue(TapToPayEligibility.checkLocation(true).ok)
        val loc = TapToPayEligibility.checkLocation(false)
        assertFalse(loc.ok)
        assertEquals("location", loc.id)
    }

    @Test
    fun sdkSupport_mapsOutcome() {
        assertTrue(TapToPayEligibility.checkSdkSupport(supported = true, detail = null).ok)
        val fail = TapToPayEligibility.checkSdkSupport(supported = false, detail = "no NFC")
        assertFalse(fail.ok)
        assertEquals("sdk_support", fail.id)
        assertEquals("no NFC", fail.detail)
        val skipped = TapToPayEligibility.checkSdkSupportSkipped("Standort erforderlich")
        assertFalse(skipped.ok)
        assertEquals("Standort erforderlich", skipped.detail)
    }

    @Test
    fun composeChecks_includesStableIdsInOrder() {
        val checks =
            TapToPayEligibility.composeChecks(
                locationOk = true,
                sdkInt = 35,
                hasNfc = true,
                keystoreHasFeature = true,
                keystoreVersion = 100,
                hasPlayStore = true,
                hasGms = true,
                securityPatch = "2026-06-01",
                now = LocalDate.of(2026, 7, 27),
                developerOptionsEnabled = false,
                isDebugBuild = false,
                internetOk = true,
                sdkSupport = TapToPayEligibility.checkSdkSupport(true, null),
            )
        assertEquals(
            listOf(
                "location",
                "android_version",
                "nfc",
                "hardware_keystore",
                "gms",
                "security_patch",
                "developer_options",
                "internet",
                "sdk_support",
            ),
            checks.map { it.id },
        )
        assertTrue(checks.all { it.ok })
    }

    @Test
    fun composeChecks_locationMissingStillIncludesAllRows() {
        val checks =
            TapToPayEligibility.composeChecks(
                locationOk = false,
                sdkInt = 35,
                hasNfc = false,
                keystoreHasFeature = true,
                keystoreVersion = 100,
                hasPlayStore = true,
                hasGms = false,
                securityPatch = "2026-06-01",
                now = LocalDate.of(2026, 7, 27),
                developerOptionsEnabled = false,
                isDebugBuild = true,
                internetOk = true,
                sdkSupport = TapToPayEligibility.checkSdkSupportSkipped("Standortberechtigung erforderlich"),
            )
        assertEquals(9, checks.size)
        assertFalse(checks.first { it.id == "location" }.ok)
        assertFalse(checks.first { it.id == "nfc" }.ok)
        assertFalse(checks.first { it.id == "sdk_support" }.ok)
        assertTrue(checks.first { it.id == "android_version" }.ok)
        assertNull(checks.first { it.id == "developer_options" }.detail)
    }

    @Test
    fun toJsonArray_serialisesIdOkDetail() {
        val json =
            TapToPayEligibility.toJsonArray(
                listOf(
                    EligibilityCheck("nfc", false, "Kein NFC"),
                    EligibilityCheck("location", true, null),
                ),
            )
        assertEquals(2, json.length())
        assertEquals("nfc", json.getJSONObject(0).getString("id"))
        assertFalse(json.getJSONObject(0).getBoolean("ok"))
        assertEquals("Kein NFC", json.getJSONObject(0).getString("detail"))
        assertTrue(json.getJSONObject(1).getBoolean("ok"))
        assertFalse(json.getJSONObject(1).has("detail"))
    }
}
