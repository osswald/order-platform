import { isAndroidApp } from '@/api'

export const MODEM_HANDSHAKE_EVENT = 'vendiqo-modem-handshake'
export const MODEM_HANDSHAKE_TIMEOUT_MS = 20_000

/** Waiter display name match for the Android dial-up easter egg. */
export function isEdiWaiterName(name: string | null | undefined): boolean {
  return String(name ?? '').trim().toLowerCase() === 'edi'
}

export function shouldRunEdiModemHandshake(name: string | null | undefined): boolean {
  return isAndroidApp() && isEdiWaiterName(name)
}

type ModemHandshakeDetail = { ok?: boolean }

/**
 * Ask the Android bridge to play the modem handshake.
 * Resolves when the native layer finishes (ok or soft-fail) or after a timeout.
 * Never rejects — login must not get stuck.
 */
export function awaitAndroidModemHandshake(
  timeoutMs: number = MODEM_HANDSHAKE_TIMEOUT_MS,
): Promise<boolean> {
  return new Promise((resolve) => {
    let settled = false
    const finish = (ok: boolean) => {
      if (settled) return
      settled = true
      window.clearTimeout(timer)
      window.removeEventListener(MODEM_HANDSHAKE_EVENT, onEvent as EventListener)
      resolve(ok)
    }

    const onEvent = (event: Event) => {
      const detail = (event as CustomEvent<ModemHandshakeDetail>).detail
      finish(detail?.ok !== false)
    }

    const timer = window.setTimeout(() => finish(false), timeoutMs)
    window.addEventListener(MODEM_HANDSHAKE_EVENT, onEvent as EventListener)

    try {
      const play = window.AndroidApp?.playModemHandshake
      if (typeof play !== 'function') {
        finish(false)
        return
      }
      play()
    } catch {
      finish(false)
    }
  })
}
