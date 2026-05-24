package ch.vendiqo.app

import android.Manifest
import android.app.Activity
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.pm.PackageManager
import android.util.Base64
import android.webkit.JavascriptInterface
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

class BluetoothPrinterBridge(private val activity: Activity) {
    private val prefs = activity.getSharedPreferences("bluetooth_printer", Context.MODE_PRIVATE)
    private val sppUuid: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

    private fun adapter() = activity.getSystemService(BluetoothManager::class.java)?.adapter

    private fun hasConnectPermission(): Boolean {
        return activity.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
    }

    private fun ok(vararg pairs: Pair<String, Any?>): String {
        val json = JSONObject()
        json.put("ok", true)
        for ((key, value) in pairs) json.put(key, value)
        return json.toString()
    }

    private fun error(message: String): String {
        return JSONObject()
            .put("ok", false)
            .put("error", message)
            .toString()
    }

    @JavascriptInterface
    fun isAvailable(): Boolean = adapter() != null

    @JavascriptInterface
    fun permissionStatus(): String {
        return ok(
            "available" to (adapter() != null),
            "granted" to hasConnectPermission(),
        )
    }

    @JavascriptInterface
    fun requestPermissions(): String {
        activity.runOnUiThread {
            activity.requestPermissions(
                arrayOf(
                    Manifest.permission.BLUETOOTH_CONNECT,
                    Manifest.permission.BLUETOOTH_SCAN,
                ),
                PERMISSION_REQUEST_CODE,
            )
        }
        return ok("requested" to true, "granted" to hasConnectPermission())
    }

    @JavascriptInterface
    fun listPairedPrinters(): String {
        if (!hasConnectPermission()) return error("Bluetooth permission is missing.")
        val bt = adapter() ?: return error("Bluetooth is not available.")
        val devices = JSONArray()
        return try {
            for (device in bt.bondedDevices) {
                devices.put(
                    JSONObject()
                        .put("name", device.name ?: device.address)
                        .put("address", device.address)
                        .put("bondState", device.bondState),
                )
            }
            ok("printers" to devices)
        } catch (e: SecurityException) {
            error(e.message ?: "Bluetooth permission denied.")
        }
    }

    @JavascriptInterface
    fun getSelectedPrinter(): String {
        return ok("address" to prefs.getString("address", ""))
    }

    @JavascriptInterface
    fun setSelectedPrinter(address: String?): String {
        val clean = address?.trim().orEmpty()
        if (clean.isEmpty()) return error("Printer address is empty.")
        prefs.edit().putString("address", clean).apply()
        return ok("address" to clean)
    }

    @JavascriptInterface
    fun printEscposBase64(payload: String?): String {
        if (!hasConnectPermission()) return error("Bluetooth permission is missing.")
        val address = prefs.getString("address", "")?.trim().orEmpty()
        if (address.isEmpty()) return error("No Bluetooth printer selected.")
        val bt = adapter() ?: return error("Bluetooth is not available.")
        val bytes = try {
            Base64.decode(payload.orEmpty(), Base64.DEFAULT)
        } catch (e: IllegalArgumentException) {
            return error("Invalid ESC/POS payload.")
        }
        return try {
            val device = bt.getRemoteDevice(address)
            val socket = device.createRfcommSocketToServiceRecord(sppUuid)
            socket.use { s ->
                s.connect()
                s.outputStream.use { out ->
                    out.write(bytes)
                    out.flush()
                }
            }
            ok("address" to address, "bytes" to bytes.size)
        } catch (e: SecurityException) {
            error(e.message ?: "Bluetooth permission denied.")
        } catch (e: Exception) {
            error(e.message ?: "Bluetooth print failed.")
        }
    }

    companion object {
        const val PERMISSION_REQUEST_CODE = 4101
    }
}
