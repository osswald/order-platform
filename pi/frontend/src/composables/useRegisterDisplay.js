import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { useCart } from './useCart'
import { useEventContext } from './useEventContext'

let pickupHoldUntil = 0
let idleTimerId = null

export function idleDisplayPayload() {
  return {
    state: 'idle',
    lines: [],
    total_cents: 0,
    show_twint: false,
    twint_qr_data_url: null,
    voucher_lines: [],
  }
}

export function canSetIdleNow() {
  return Date.now() >= pickupHoldUntil
}

export function clearPickupHold() {
  pickupHoldUntil = 0
  if (idleTimerId != null) {
    clearTimeout(idleTimerId)
    idleTimerId = null
  }
}

export function holdPickupDisplay(ms = 10000) {
  pickupHoldUntil = Date.now() + ms
}

export function useRegisterDisplay() {
  const route = useRoute()
  const router = useRouter()
  const { event, currency } = useEventContext()
  const { cartLines, cartTotalCents } = useCart()

  const registerUuid = computed(() => String(route.params.registerUuid || ''))
  const register = computed(
    () =>
      (event.value?.configuration?.cash_registers || []).find(
        (reg) => String(reg.uuid) === registerUuid.value,
      ) || null,
  )
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

  async function pushDisplayPayload(payload) {
    if (!event.value?.id || !register.value?.uuid) return
    try {
      await api(`/v1/registers/${encodeURIComponent(register.value.uuid)}/display`, {
        method: 'PUT',
        body: JSON.stringify({
          event_id: event.value.id,
          payload: {
            register_name: register.value.name,
            currency: currency.value,
            ...payload,
          },
        }),
      })
    } catch {
      /* second screen is best-effort */
    }
  }

  async function updateDisplay(extra = {}) {
    if (!event.value?.id || !register.value?.uuid) return
    await pushDisplayPayload({
      lines: cartLines.value,
      total_cents: cartTotalCents.value,
      ...extra,
    })
  }

  async function setDisplayIdle() {
    if (!canSetIdleNow()) return
    await pushDisplayPayload(idleDisplayPayload())
  }

  function scheduleIdleAfterPickup(ms = 10000) {
    if (idleTimerId != null) {
      clearTimeout(idleTimerId)
      idleTimerId = null
    }
    holdPickupDisplay(ms)
    idleTimerId = setTimeout(() => {
      idleTimerId = null
      pickupHoldUntil = 0
      setDisplayIdle()
    }, ms)
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
    pushDisplayPayload,
    setDisplayIdle,
    scheduleIdleAfterPickup,
    clearPickupHold,
    hubRoute,
    orderRoute,
    displayRoute,
  }
}
