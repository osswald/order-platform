import { ref } from 'vue'

export interface WaiterSession {
  uuid: string
  name: string
}

export interface RegisterSession {
  uuid: string
  name: string
}

export interface PersistedWaiterSession extends WaiterSession {
  eventId: number
}

export interface PersistedRegisterSession extends RegisterSession {
  eventId: number
}

export const selectedEventId = ref<number | null>(null)
export const waiter = ref<WaiterSession | null>(null)
export const activeTableNumber = ref<number | null>(null)
export const registerSession = ref<RegisterSession | null>(null)

export const WAITER_SESSION_KEY = 'pi_waiter_session'
export const REGISTER_SESSION_KEY = 'pi_register_session'

export function persistWaiterSession(session: PersistedWaiterSession): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(WAITER_SESSION_KEY, JSON.stringify(session))
  } catch {
    /* ignore quota / private mode */
  }
}

export function restoreWaiterSession(): void {
  if (typeof localStorage === 'undefined') return
  try {
    const raw = localStorage.getItem(WAITER_SESSION_KEY)
    if (!raw) return
    const data = JSON.parse(raw) as Partial<PersistedWaiterSession>
    if (!data?.uuid || data.eventId == null) return
    selectedEventId.value = Number(data.eventId)
    waiter.value = { uuid: String(data.uuid), name: String(data.name || '') }
  } catch {
    localStorage.removeItem(WAITER_SESSION_KEY)
  }
}

export function persistRegisterSession(session: PersistedRegisterSession): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(REGISTER_SESSION_KEY, JSON.stringify(session))
  } catch {
    /* ignore */
  }
}

export function restoreRegisterSession(): void {
  if (typeof localStorage === 'undefined') return
  try {
    const raw = localStorage.getItem(REGISTER_SESSION_KEY)
    if (!raw) return
    const data = JSON.parse(raw) as Partial<PersistedRegisterSession>
    if (!data?.uuid || data.eventId == null) return
    selectedEventId.value = Number(data.eventId)
    registerSession.value = { uuid: String(data.uuid), name: String(data.name || '') }
  } catch {
    localStorage.removeItem(REGISTER_SESSION_KEY)
  }
}

restoreWaiterSession()
restoreRegisterSession()
