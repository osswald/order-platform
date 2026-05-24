import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as store from '../store'
import { api } from '../api'

export function useRegisterDisplay() {
  const route = useRoute()
  const router = useRouter()

  const registerUuid = computed(() => String(route.params.registerUuid || ''))
  const event = computed(() => store.selectedEvent.value)
  const register = computed(
    () =>
      (event.value?.configuration?.cash_registers || []).find(
        (reg) => String(reg.uuid) === registerUuid.value,
      ) || null,
  )
  const currency = computed(() => event.value?.currency || 'EUR')

  function registerDisplayPath() {
    return router.resolve({
      name: 'register-display',
      params: { registerUuid: registerUuid.value },
    }).href
  }

  function registerDisplayUrl() {
    const path = registerDisplayPath()
    if (typeof window === 'undefined') return path
    return `${window.location.origin}${path}`
  }

  async function updateDisplay(extra = {}) {
    if (!event.value?.id || !register.value?.uuid) return
    try {
      await api(`/v1/registers/${encodeURIComponent(register.value.uuid)}/display`, {
        method: 'PUT',
        body: JSON.stringify({
          event_id: event.value.id,
          payload: {
            register_name: register.value.name,
            lines: store.cartLines.value,
            total_cents: store.cartTotalCents.value,
            currency: currency.value,
            ...extra,
          },
        }),
      })
    } catch {
      /* second screen is best-effort */
    }
  }

  function hubRoute() {
    return { name: 'register-hub', params: { registerUuid: registerUuid.value } }
  }

  function orderRoute() {
    return { name: 'register-order', params: { registerUuid: registerUuid.value } }
  }

  function displayRoute() {
    return { name: 'register-display', params: { registerUuid: registerUuid.value } }
  }

  return {
    registerUuid,
    event,
    register,
    currency,
    registerDisplayPath,
    registerDisplayUrl,
    updateDisplay,
    hubRoute,
    orderRoute,
    displayRoute,
  }
}
