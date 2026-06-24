import { ref } from 'vue'

export const selectedEventId = ref(null)
/** @type {import('vue').Ref<{ id: number, name: string } | null>} */
export const waiter = ref(null)
export const activeTableNumber = ref(null)

/** @type {import('vue').Ref<{ uuid: string, name: string } | null>} */
export const registerSession = ref(null)

export const WAITER_SESSION_KEY = 'pi_waiter_session'
export const REGISTER_SESSION_KEY = 'pi_register_session'

export function persistWaiterSession(session) {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(WAITER_SESSION_KEY, JSON.stringify(session))
  } catch {
    /* ignore quota / private mode */
  }
}

export function restoreWaiterSession() {
  if (typeof localStorage === 'undefined') return
  try {
    const raw = localStorage.getItem(WAITER_SESSION_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (!data?.uuid || data.eventId == null) return
    selectedEventId.value = Number(data.eventId)
    waiter.value = { uuid: String(data.uuid), name: String(data.name || '') }
  } catch {
    localStorage.removeItem(WAITER_SESSION_KEY)
  }
}

export function persistRegisterSession(session) {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(REGISTER_SESSION_KEY, JSON.stringify(session))
  } catch {
    /* ignore */
  }
}

export function restoreRegisterSession() {
  if (typeof localStorage === 'undefined') return
  try {
    const raw = localStorage.getItem(REGISTER_SESSION_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (!data?.uuid || data.eventId == null) return
    selectedEventId.value = Number(data.eventId)
    registerSession.value = { uuid: String(data.uuid), name: String(data.name || '') }
  } catch {
    localStorage.removeItem(REGISTER_SESSION_KEY)
  }
}

restoreWaiterSession()
restoreRegisterSession()
