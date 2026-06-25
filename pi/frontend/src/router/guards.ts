import type { Router } from 'vue-router'
import * as store from '@/store'
import '@/types/router'

const ROUTES_WITHOUT_BUNDLE = new Set(['events', 'admin-unlock', 'admin'])

export function setupRouterGuards(router: Router): void {
  router.beforeEach(async (to) => {
    if (to.meta.requiresAdmin && store.adminRequiresPin() && !store.adminUnlocked.value) {
      return { name: 'admin-unlock', query: { redirect: to.fullPath } }
    }
    if (to.meta.requiresBundle && !store.bundleReady()) {
      if (!ROUTES_WITHOUT_BUNDLE.has(String(to.name))) {
        try {
          await store.refreshBundle()
        } catch {
          /* bundle unavailable */
        }
      }
      if (!store.bundleReady()) {
        if (ROUTES_WITHOUT_BUNDLE.has(String(to.name))) {
          return true
        }
        return { name: 'events' }
      }
    }
    if (to.meta.requiresEvent && store.selectedEventId.value == null) {
      return { name: 'events' }
    }
    if (to.meta.requiresWaiter && !store.waiter.value) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (to.meta.requiresRegister) {
      const uuid = String(to.params.registerUuid || '')
      const session = store.registerSession.value
      if (!session || String(session.uuid) !== uuid) {
        return { name: 'registers', query: { redirect: to.fullPath } }
      }
    }
    return true
  })
}
