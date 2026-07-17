import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { setupRouterGuards } from './guards'
import '@/types/router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: () => ({ name: 'events' }) },
  {
    path: '/setup',
    name: 'setup',
    component: () => import('../views/SetupPairingView.vue'),
    meta: { title: 'Pi koppeln', fullscreen: true },
  },
  {
    path: '/admin/unlock',
    name: 'admin-unlock',
    component: () => import('../views/AdminUnlockView.vue'),
    meta: { title: 'Admin', hideNav: true },
  },
  {
    path: '/admin',
    component: () => import('../views/admin/AdminShell.vue'),
    meta: { requiresAdmin: true },
    children: [
      {
        path: '',
        name: 'admin',
        component: () => import('../views/admin/AdminHubView.vue'),
        meta: { title: 'Admin' },
      },
      {
        path: 'sync',
        name: 'admin-sync',
        component: () => import('../views/admin/AdminSyncView.vue'),
        meta: { title: 'Synchronisation' },
      },
      {
        path: 'operations',
        component: () => import('../views/admin/operations/AdminOperationsShell.vue'),
        meta: { title: 'Betrieb', requiresBundle: true },
        children: [
          {
            path: '',
            name: 'admin-operations',
            component: () => import('../views/admin/operations/AdminOperationsHubView.vue'),
          },
          {
            path: 'test-print',
            name: 'admin-operations-test-print',
            component: () => import('../views/admin/operations/AdminOperationsTestPrintView.vue'),
            meta: { title: 'Testdruck' },
          },
          {
            path: 'kitchen',
            name: 'admin-operations-kitchen',
            component: () => import('../views/admin/operations/AdminOperationsKitchenView.vue'),
            meta: { title: 'Küchenmonitor' },
          },
          {
            path: 'pickup',
            name: 'admin-operations-pickup',
            component: () => import('../views/admin/operations/AdminOperationsPickupView.vue'),
            meta: { title: 'Pickup Screen' },
          },
          {
            path: 'display',
            name: 'admin-operations-display',
            component: () => import('../views/admin/operations/AdminOperationsCustomerDisplayView.vue'),
            meta: { title: 'Kundendisplay' },
          },
        ],
      },
      {
        path: 'unpair',
        name: 'admin-unpair',
        component: () => import('../views/admin/AdminUnpairView.vue'),
        meta: { title: 'Entkoppeln' },
      },
    ],
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
    path: '/event/mode',
    name: 'event-mode',
    component: () => import('../views/EventModeView.vue'),
    meta: { title: 'Modus', requiresBundle: true, requiresEvent: true },
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
    path: '/print-failures',
    name: 'print-failures',
    component: () => import('../views/PrintFailuresView.vue'),
    meta: { title: 'Druckfehler', requiresBundle: true, requiresEvent: true, requiresWaiter: true },
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
    path: '/kitchen/:printerSlug/:view?',
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
    meta: { title: 'Kasse', requiresBundle: true, requiresEvent: true, requiresRegister: true },
  },
  {
    path: '/register/:registerUuid/order',
    name: 'register-order',
    component: () => import('../views/RegisterOrderView.vue'),
    meta: { title: 'Kasse', requiresBundle: true, requiresEvent: true, requiresRegister: true, fullscreen: true },
  },
  {
    path: '/register/:registerUuid/pay/:orderId',
    name: 'register-pay',
    component: () => import('../views/RegisterPayView.vue'),
    meta: { title: 'Kasse', requiresBundle: true, requiresEvent: true, requiresRegister: true, fullscreen: true },
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

setupRouterGuards(router)

export default router
