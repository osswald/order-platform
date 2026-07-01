import { computed } from 'vue'
import { useBundle } from './useBundle'
import { useWaiterSession } from './useWaiterSession'

/** Selected event, waiter, and common helpers for order/payment views. */
export function useEventContext() {
  const { waiter, selectedEvent, selectedEventId, setWaiter, validateWaiterSession } = useWaiterSession()
  const { showToast, patchEventArticles, patchEventStock, refreshBundle } = useBundle()

  const event = selectedEvent
  const currency = computed(() => event.value?.currency || 'EUR')

  return {
    event,
    selectedEvent,
    currency,
    waiter: computed(() => waiter.value),
    selectedEventId,
    setWaiter,
    validateWaiterSession,
    showToast,
    patchEventArticles,
    patchEventStock,
    refreshBundle,
  }
}
