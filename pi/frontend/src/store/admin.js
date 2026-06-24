import { ref } from 'vue'
import { api } from '../api'
import { bundle, bundleReady } from './bundle'

const ADMIN_SESSION_KEY = 'pi_admin_unlocked'

export const adminUnlocked = ref(sessionStorage.getItem(ADMIN_SESSION_KEY) === '1')

export function setAdminUnlocked(ok) {
  adminUnlocked.value = ok
  if (ok) sessionStorage.setItem(ADMIN_SESSION_KEY, '1')
  else sessionStorage.removeItem(ADMIN_SESSION_KEY)
}

export function clearAdminSession() {
  setAdminUnlocked(false)
}

export function adminRequiresPin() {
  if (!bundleReady()) return false
  const hashes = bundle.value?.admin_pin_hashes
  return Array.isArray(hashes) && hashes.length > 0
}

export async function verifyAdminPin(pin) {
  await api('/v1/admin/verify', {
    method: 'POST',
    body: JSON.stringify({ pin }),
  })
  setAdminUnlocked(true)
}
