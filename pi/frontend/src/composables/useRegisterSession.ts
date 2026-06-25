import { computed } from 'vue'
import {
  registerSession,
  selectedEvent,
  selectedEventId,
  setRegisterSession,
  validateRegisterSession,
} from '@/store'

export function useRegisterSession() {
  return {
    registerSession: computed(() => registerSession.value),
    selectedEvent,
    selectedEventId: computed(() => selectedEventId.value),
    setRegisterSession,
    validateRegisterSession,
    isLoggedIn: computed(() => Boolean(registerSession.value)),
  }
}
