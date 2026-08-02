import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { computed, ref } from 'vue'

const probeApiBase = vi.fn()
const notePiReachable = vi.fn()
const fetchSetupStatus = vi.fn(async () => ({ configured: true }))
const refreshBundle = vi.fn(async () => undefined)
const usePiConnectivityKeepalive = vi.fn()

vi.mock('@/utils/probeApiBase', () => ({
  probeApiBase: (...args: unknown[]) => probeApiBase(...args),
}))

vi.mock('@/composables/usePiConnectivity', () => ({
  notePiReachable: (...args: unknown[]) => notePiReachable(...args),
  usePiConnectivityKeepalive: (...args: unknown[]) => usePiConnectivityKeepalive(...args),
}))

vi.mock('@/composables/useBundleRefresh', () => ({
  useBundleRefresh: vi.fn(),
}))

vi.mock('@/composables/useBundle', () => ({
  useBundle: () => ({
    bundleReady: () => true,
    refreshBundle,
  }),
}))

vi.mock('@/composables/useSetupStatus', () => ({
  useSetupStatus: () => ({
    emulatedPrinter: ref(false),
    fetchSetupStatus,
  }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ toast: ref(null) }),
}))

vi.mock('@/composables/useWaiterSession', () => ({
  useWaiterSession: () => ({
    waiter: ref(null),
    selectedEventId: ref(null),
  }),
}))

vi.mock('@/composables/useStationPrintFailures', () => ({
  startWaiterPrintFailurePolling: vi.fn(),
  stopWaiterPrintFailurePolling: vi.fn(),
}))

vi.mock('@/composables/useMediaQuery', () => ({
  useMediaQuery: () => computed(() => false),
}))

vi.mock('@/api', () => ({
  isAndroidApp: () => false,
}))

vi.mock('@/utils/androidInsets', () => ({
  applyAndroidSafeAreaInsets: vi.fn(),
}))

vi.mock('@/utils/pickPaymentType', () => ({
  pickerOpen: ref(false),
  pickerTypes: ref([]),
  pickerAmountLabel: ref(''),
  twintQrOpen: ref(false),
  twintQrDataUrl: ref(''),
  twintQrAmountLabel: ref(''),
  confirmPaymentType: vi.fn(),
  cancelPaymentType: vi.fn(),
  confirmTwintQr: vi.fn(),
  cancelTwintQr: vi.fn(),
}))

vi.mock('@/utils/resolvePayment', () => ({
  terminalPaymentBusy: ref(false),
}))

vi.mock('@/utils/paymentReceiptPrompt', () => ({
  receiptPromptOpen: ref(false),
  receiptPromptStep: ref('ask'),
  receiptPromptTargets: ref([]),
  receiptPromptBusy: ref(false),
  confirmReceiptPrintYes: vi.fn(),
  confirmReceiptPrintNo: vi.fn(),
  cancelReceiptPrompt: vi.fn(),
  selectReceiptStation: vi.fn(),
}))

vi.mock('@/components/ShiftOpenDialog.vue', () => ({
  default: { template: '<div />' },
}))
vi.mock('@/components/ShiftCloseDialog.vue', () => ({
  default: { template: '<div />' },
}))
vi.mock('@/components/PaymentTypePickerSheet.vue', () => ({
  default: { template: '<div />' },
}))
vi.mock('@/components/PaymentReceiptPromptSheet.vue', () => ({
  default: { template: '<div />' },
}))
vi.mock('@/components/TwintQrSheet.vue', () => ({
  default: { template: '<div />' },
}))
vi.mock('@/components/EmulatedReceiptsPanel.vue', () => ({
  default: { template: '<div />' },
}))
vi.mock('@/components/ReceiptBottomSheet.vue', () => ({
  default: { template: '<div />' },
}))

import App from './App.vue'

describe('App cold-start connectivity', () => {
  beforeEach(() => {
    probeApiBase.mockReset()
    notePiReachable.mockReset()
    fetchSetupStatus.mockReset()
    fetchSetupStatus.mockResolvedValue({ configured: true })
  })

  async function mountApp(initialName: string) {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'hub', component: { template: '<div/>' } },
        { path: '/connection-setup', name: 'connection-setup', component: { template: '<div/>' } },
        { path: '/setup', name: 'setup', component: { template: '<div/>' } },
      ],
    })
    await router.push({ name: initialName })
    await router.isReady()
    const replace = vi.spyOn(router, 'replace')
    mount(App, { global: { plugins: [router] } })
    await flushPromises()
    return { replace }
  }

  it('redirects to connection-setup when startup probe fails (hard path unchanged)', async () => {
    probeApiBase.mockResolvedValue({ reachable: false, reason: 'network' })
    const { replace } = await mountApp('hub')
    expect(probeApiBase).toHaveBeenCalled()
    expect(replace).toHaveBeenCalledWith({ name: 'connection-setup' })
    expect(notePiReachable).not.toHaveBeenCalled()
  })

  it('seeds mid-session reachable state after successful startup probe', async () => {
    probeApiBase.mockResolvedValue({ reachable: true })
    const { replace } = await mountApp('hub')
    expect(notePiReachable).toHaveBeenCalled()
    expect(replace).not.toHaveBeenCalledWith({ name: 'connection-setup' })
  })
})
