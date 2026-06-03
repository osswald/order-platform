import { api, isAndroidApp } from '../api'
import { isAndroidTerminalAvailable } from './androidTerminal'

const CACHE_MS = 15_000
let cloudCache = { at: 0, reachable: false, reason: null }

export function isStripeTerminalAndroidReady() {
  return isAndroidTerminalAvailable() || isAndroidApp()
}

export async function checkCloudReachable(force = false) {
  const now = Date.now()
  if (!force && now - cloudCache.at < CACHE_MS) {
    return { reachable: cloudCache.reachable, reason: cloudCache.reason }
  }
  try {
    const res = await api('/v1/cloud/reachable')
    cloudCache = {
      at: now,
      reachable: Boolean(res?.reachable),
      reason: res?.reason || null,
    }
  } catch {
    cloudCache = { at: now, reachable: false, reason: 'probe_failed' }
  }
  return { reachable: cloudCache.reachable, reason: cloudCache.reason }
}

export function stripeTerminalDisabledHint(androidReady, cloudReady) {
  if (!androidReady) return 'Nur in der Android-App verfügbar.'
  if (!cloudReady) return 'Cloud-Verbindung erforderlich.'
  return null
}

export async function stripeTerminalPickerEntry() {
  const androidReady = isStripeTerminalAndroidReady()
  const { reachable: cloudReady } = await checkCloudReachable()
  const hint = stripeTerminalDisabledHint(androidReady, cloudReady)
  return {
    value: 'stripe_terminal',
    disabled: Boolean(hint),
    hint: hint || undefined,
  }
}
