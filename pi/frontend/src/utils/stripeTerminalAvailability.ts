import { api, isAndroidApp } from '@/api'
import type { CloudReachableResponse } from '@/types/api'
import {
  checkTapToPayDeviceSupport,
  isAndroidTerminalAvailable,
  type TapToPaySupportStatus,
} from './androidTerminal'
import type { PaymentPickerEntry } from './pickPaymentType'

const CACHE_MS = 15_000
let cloudCache: { at: number; reachable: boolean; reason: string | null } = {
  at: 0,
  reachable: false,
  reason: null,
}

const DEVICE_UNSUPPORTED_HINT = 'Gerät unterstützt keine Kartenzahlung (Tap to Pay).'
const LOCATION_HINT = 'Standortberechtigung für Kartenzahlung erforderlich.'

export function isStripeTerminalAndroidReady(): boolean {
  return isAndroidTerminalAvailable() || isAndroidApp()
}

export async function checkCloudReachable(force = false): Promise<{
  reachable: boolean
  reason: string | null
}> {
  const now = Date.now()
  if (!force && now - cloudCache.at < CACHE_MS) {
    return { reachable: cloudCache.reachable, reason: cloudCache.reason }
  }
  try {
    const res = await api<CloudReachableResponse>('/v1/cloud/reachable')
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

export function stripeTerminalDisabledHint(
  androidReady: boolean,
  cloudReady: boolean,
  deviceSupport: TapToPaySupportStatus = { status: 'unknown' },
): string | null {
  if (!androidReady) return 'Nur in der Android-App verfügbar.'
  if (!cloudReady) return 'Cloud-Verbindung erforderlich.'
  if (deviceSupport.status === 'check_failed') {
    return deviceSupport.error || LOCATION_HINT
  }
  if (deviceSupport.status === 'unsupported') {
    return DEVICE_UNSUPPORTED_HINT
  }
  return null
}

export async function stripeTerminalPickerEntry(): Promise<PaymentPickerEntry> {
  const androidReady = isStripeTerminalAndroidReady()
  const { reachable: cloudReady } = await checkCloudReachable()
  const deviceSupport = androidReady ? checkTapToPayDeviceSupport() : { status: 'unknown' as const }
  const hint = stripeTerminalDisabledHint(androidReady, cloudReady, deviceSupport)
  return {
    value: 'stripe_terminal',
    disabled: Boolean(hint),
    hint: hint || undefined,
  }
}
