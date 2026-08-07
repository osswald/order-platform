package ch.vendiqo.app

import android.app.Activity
import android.content.Context
import android.view.inputmethod.InputMethodManager

/** Hides the soft keyboard (IME). JVM-testable via [hide]. */
fun interface SoftKeyboardHider {
    fun hide()
}

fun softKeyboardHiderForActivity(activity: Activity): SoftKeyboardHider =
    SoftKeyboardHider {
        val imm = activity.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
            ?: return@SoftKeyboardHider
        val view = activity.currentFocus ?: activity.window?.decorView ?: return@SoftKeyboardHider
        imm.hideSoftInputFromWindow(view.windowToken, 0)
    }
