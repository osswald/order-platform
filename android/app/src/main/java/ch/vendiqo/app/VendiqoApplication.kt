package ch.vendiqo.app

import android.app.Application
import com.stripe.stripeterminal.TerminalApplicationDelegate

class VendiqoApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        TerminalApplicationDelegate.onCreate(this)
    }
}
