import { computed } from 'vue'
import {
  selectedEvent,
  selectedEventId,
  setWaiter,
  validateWaiterSession,
  waiter,
} from '@/store'

export function useWaiterSession() {
  return {
    waiter: computed(() => waiter.value),
    selectedEvent,
    selectedEventId: computed(() => selectedEventId.value),
    setWaiter,
    validateWaiterSession,
    isLoggedIn: computed(() => Boolean(waiter.value)),
  }
}
