import * as store from '@/store'

export function resetStore() {
  store.bundle.value = null
  store.selectedEventId.value = null
  store.waiter.value = null
  store.registerSession.value = null
  store.cartLines.value = []
  store.orderDiscount.value = null
  store.clearAdminSession()
  localStorage.clear()
  sessionStorage.clear()
}
