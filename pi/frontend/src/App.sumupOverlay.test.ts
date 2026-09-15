import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

const {
  terminalPaymentBusy,
  sumupPaymentFailureMessage,
  cancelActiveSumupPayment,
  dismissSumupPaymentFailure,
} = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref } = require('vue') as typeof import('vue')
  return {
    terminalPaymentBusy: ref(false),
    sumupPaymentFailureMessage: ref<string | null>(null),
    cancelActiveSumupPayment: vi.fn(),
    dismissSumupPaymentFailure: vi.fn(),
  }
})

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'hub', meta: {}, path: '/' }),
  useRouter: () => ({ replace: vi.fn(), afterEach: vi.fn() }),
  RouterView: defineComponent({ name: 'RouterView', setup: () => () => h('div') }),
}))

vi.mock('@/utils/resolvePayment', () => ({
  terminalPaymentBusy,
  sumupPaymentFailureMessage,
  cancelActiveSumupPayment,
  dismissSumupPaymentFailure,
}))

vi.mock('@/utils/pickPaymentType', () => ({
  pickerOpen: { value: false },
  pickerTypes: { value: [] },
  pickerAmountLabel: { value: '' },
  twintQrOpen: { value: false },
  twintQrDataUrl: { value: '' },
  twintQrAmountLabel: { value: '' },
  confirmPaymentType: vi.fn(),
  cancelPaymentType: vi.fn(),
  confirmTwintQr: vi.fn(),
  cancelTwintQr: vi.fn(),
}))

vi.mock('@/utils/paymentReceiptPrompt', () => ({
  receiptPromptOpen: { value: false },
  receiptPromptStep: { value: 'ask' },
  receiptPromptTargets: { value: [] },
  receiptPromptBusy: { value: false },
  confirmReceiptPrintYes: vi.fn(),
  confirmReceiptPrintNo: vi.fn(),
  cancelReceiptPrompt: vi.fn(),
  selectReceiptStation: vi.fn(),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ toast: { value: null } }),
}))

vi.mock('@/composables/useBundle', () => ({
  useBundle: () => ({ bundleReady: () => true, refreshBundle: vi.fn() }),
}))

vi.mock('@/composables/useBundleRefresh', () => ({
  useBundleRefresh: vi.fn(),
}))

vi.mock('@/composables/usePiConnectivity', () => ({
  notePiReachable: vi.fn(),
  usePiConnectivityKeepalive: vi.fn(),
}))

vi.mock('@/composables/useSetupStatus', () => ({
  useSetupStatus: () => ({
    emulatedPrinter: { value: false },
    fetchSetupStatus: vi.fn(async () => ({ configured: true })),
  }),
}))

vi.mock('@/composables/useWaiterSession', () => ({
  useWaiterSession: () => ({ waiter: { value: null }, selectedEventId: { value: null } }),
}))

vi.mock('@/composables/useStationPrintFailures', () => ({
  startWaiterPrintFailurePolling: vi.fn(),
  stopWaiterPrintFailurePolling: vi.fn(),
}))

vi.mock('@/composables/useAndroidImmersiveDisplay', () => ({
  useAndroidImmersiveDisplay: vi.fn(),
}))

vi.mock('@/composables/useMediaQuery', () => ({
  useMediaQuery: () => ({ value: false }),
}))

vi.mock('@/utils/probeApiBase', () => ({
  probeApiBase: vi.fn(async () => ({ reachable: true })),
}))

vi.mock('@/utils/androidInsets', () => ({
  applyAndroidSafeAreaInsets: vi.fn(),
}))

vi.mock('@/api', () => ({
  isAndroidApp: () => false,
}))

vi.mock('@/components/ShiftOpenDialog.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/ShiftCloseDialog.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/PaymentTypePickerSheet.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/PaymentReceiptPromptSheet.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/TwintQrSheet.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/EmulatedReceiptsPanel.vue', () => ({ default: { template: '<div />' } }))
vi.mock('@/components/ReceiptBottomSheet.vue', () => ({ default: { template: '<div />' } }))

import App from './App.vue'

describe('App SumUp terminal overlay', () => {
  beforeEach(() => {
    terminalPaymentBusy.value = false
    sumupPaymentFailureMessage.value = null
    cancelActiveSumupPayment.mockReset()
    dismissSumupPaymentFailure.mockReset()
  })

  it('shows Abbrechen while busy and invokes cancel', async () => {
    terminalPaymentBusy.value = true
    const wrapper = mount(App)
    await flushPromises()
    expect(wrapper.text()).toContain('Karte an das Gerät halten')
    const btn = wrapper.find('.terminal-busy-cancel')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Abbrechen')
    await btn.trigger('click')
    expect(cancelActiveSumupPayment).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('shows failure sheet and dismiss clears it', async () => {
    sumupPaymentFailureMessage.value = 'Karte abgelehnt'
    const wrapper = mount(App)
    await flushPromises()
    expect(wrapper.text()).toContain('Zahlung fehlgeschlagen')
    expect(wrapper.text()).toContain('Karte abgelehnt')
    expect(wrapper.find('.terminal-busy-cancel').exists()).toBe(false)
    await wrapper.find('.terminal-failure-dismiss').trigger('click')
    expect(dismissSumupPaymentFailure).toHaveBeenCalledOnce()
    wrapper.unmount()
  })
})
