import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import * as store from '../store'

const routes = [
  { path: '/', redirect: () => ({ name: 'events' }) },
  {
    path: '/setup',
    redirect: (to) => ({ name: 'admin', query: to.query }),
  },
  {
    path: '/admin/unlock',
    name: 'admin-unlock',
    component: () => import('../views/AdminUnlockView.vue'),
    meta: { title: 'Admin', hideNav: true },
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/AdminPanelView.vue'),
    meta: { title: 'Sync', requiresAdmin: true, nav: true, navLabel: 'Sync' },
  },
  {
    path: '/android/printer',
    name: 'android-printer',
    component: () => import('../views/AndroidPrinterSetupView.vue'),
    meta: { title: 'Bluetooth Drucker', nav: true },
  },
  {
    path: '/receipts',
    name: 'receipts',
    component: () => import('../views/ReceiptHistoryView.vue'),
    meta: { title: 'Belege', requiresBundle: true, requiresEvent: true, requiresWaiter: true, nav: true },
  },
  {
    path: '/events',
    name: 'events',
    component: () => import('../views/EventsView.vue'),
    meta: { title: 'Events', nav: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: 'Kellner', requiresBundle: true, requiresEvent: true },
  },
  {
    path: '/hub',
    name: 'hub',
    component: () => import('../views/WaiterHubView.vue'),
    meta: { title: 'Kellner', requiresBundle: true, requiresEvent: true, requiresWaiter: true, nav: true },
  },
  {
    path: '/tables/open',
    name: 'tables-open',
    component: () => import('../views/OpenTablesView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true },
  },
  {
    path: '/collective/open',
    name: 'collective-open',
    component: () => import('../views/OpenCollectiveBillsView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true },
  },
  {
    path: '/stock',
    name: 'stock',
    component: () => import('../views/StockView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true },
  },
  {
    path: '/kitchen',
    name: 'kitchen',
    component: () => import('../views/KitchenMonitorView.vue'),
    meta: { title: 'Küche', requiresBundle: true, requiresEvent: true, fullscreen: true },
  },
  {
    path: '/registers',
    name: 'registers',
    component: () => import('../views/RegisterSelectView.vue'),
    meta: { title: 'Kassen', requiresBundle: true, requiresEvent: true },
  },
  {
    path: '/register/:registerUuid',
    name: 'register-hub',
    component: () => import('../views/RegisterHubView.vue'),
    meta: { title: 'Kasse', requiresBundle: true, requiresEvent: true },
  },
  {
    path: '/register/:registerUuid/order',
    name: 'register-order',
    component: () => import('../views/RegisterOrderView.vue'),
    meta: { title: 'Kasse', requiresBundle: true, requiresEvent: true, fullscreen: true },
  },
  {
    path: '/register/:registerUuid/display',
    name: 'register-display',
    component: () => import('../views/RegisterDisplayView.vue'),
    meta: { title: 'Kundendisplay', requiresBundle: true, requiresEvent: true, fullscreen: true },
  },
  {
    path: '/pickup',
    name: 'pickup',
    component: () => import('../views/PickupScreenView.vue'),
    meta: { title: 'Pickup', requiresBundle: true, requiresEvent: true, fullscreen: true },
  },
  {
    path: '/table/new',
    name: 'table-new',
    component: () => import('../views/TableNewView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true },
  },
  {
    path: '/table/settle',
    name: 'table-settle-keypad',
    component: () => import('../views/TableSettleKeypadView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true },
  },
  {
    path: '/order',
    name: 'order',
    component: () => import('../views/OrderView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true, fullscreen: true },
  },
  {
    path: '/pay/order/:id',
    name: 'pay-order',
    component: () => import('../views/PayOrderView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true },
  },
  {
    path: '/pay/table',
    name: 'pay-table',
    component: () => import('../views/PayTableView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true, fullscreen: true },
  },
  {
    path: '/pay/collective',
    name: 'pay-collective',
    component: () => import('../views/PayCollectiveView.vue'),
    meta: { requiresBundle: true, requiresEvent: true, requiresWaiter: true, fullscreen: true },
  },
]

const router = createRouter({
  history: import.meta.env.VITE_ANDROID_APP === 'true'
    ? createWebHashHistory(import.meta.env.BASE_URL)
    : createWebHistory(import.meta.env.BASE_URL),
  routes,
})

const ROUTES_WITHOUT_BUNDLE = new Set(['events', 'admin-unlock', 'admin'])

router.beforeEach(async (to) => {
  if (to.meta.requiresAdmin && store.adminRequiresPin() && !store.adminUnlocked.value) {
    return { name: 'admin-unlock', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresBundle && !store.bundleReady()) {
    if (!ROUTES_WITHOUT_BUNDLE.has(to.name)) {
      try {
        await store.refreshBundle()
      } catch {
        /* bundle unavailable */
      }
    }
    if (!store.bundleReady()) {
      if (ROUTES_WITHOUT_BUNDLE.has(to.name)) {
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
  return true
})

export default router
