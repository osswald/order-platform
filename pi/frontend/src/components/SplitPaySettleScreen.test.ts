import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'

const {
  onGreenCheck,
  offerPaymentReceiptAfterSettle,
  showToast,
  remainingItemCount,
} = vi.hoisted(() => {
  // `ref` must be required inside hoisted — import is not initialized yet.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue') as typeof import('vue')
  return {
    onGreenCheck: vi.fn(),
    offerPaymentReceiptAfterSettle: vi.fn(),
    showToast: vi.fn(),
    remainingItemCount: vueRef(0),
  }
})

vi.mock('@/composables/useEventContext', () => ({
  useEventContext: () => ({
    event: ref({
      id: 1,
      currency: 'CHF',
      offer_payment_receipt: true,
      articles: {},
    }),
    currency: ref('CHF'),
    showToast,
  }),
}))

vi.mock('@/composables/useSplitPay', () => ({
  useSplitPay: () => ({
    groups: ref([
      {
        key: 'g1',
        name: 'Bier',
        additionLabels: [],
        basketQty: 1,
        totalQty: 1,
        unitCents: 500,
        lineTotalCents: 500,
        discount: null,
        note: '',
        lines: [],
      },
    ]),
    loading: ref(false),
    paying: ref(false),
    qtyModalOpen: ref(false),
    qtyModalGroup: ref(null),
    totalCents: ref(500),
    basketCents: ref(500),
    restCents: ref(0),
    basketItemCount: ref(1),
    remainingItemCount,
    topGroups: ref([
      {
        key: 'g1',
        name: 'Bier',
        additionLabels: [],
        basketQty: 1,
        totalQty: 1,
        unitCents: 500,
        lineTotalCents: 500,
        discount: null,
        note: '',
        lines: [],
      },
    ]),
    bottomGroups: ref([]),
    moveAllToBottom: vi.fn(),
    moveAllToTop: vi.fn(),
    bumpBasket: vi.fn(),
    openQtyModal: vi.fn(),
    onQtyConfirm: vi.fn(),
    selectionsPayload: () => [],
    reload: vi.fn(),
    onGreenCheck,
    rawBasketCents: ref(500),
    voucherCreditCents: ref(0),
    fixedCents: ref(0),
  }),
}))

vi.mock('@/utils/paymentReceiptPrompt', () => ({
  offerPaymentReceiptAfterSettle,
}))

import SplitPaySettleScreen from './SplitPaySettleScreen.vue'

function mountSettleScreen() {
  return mount(SplitPaySettleScreen, {
    props: {
      emptyText: 'leer',
      settledToast: 'Abgerechnet.',
      loadSummary: async () => ({ remaining_cents: 500, lines: [] }),
      settlePartialPath: () => '/v1/tables/1/settle-partial',
    },
    global: {
      stubs: {
        SplitPayHeader: true,
        SplitPayLineRow: true,
        SplitPayVoucherRow: true,
        QtyInputModal: true,
        PayTableActionsSheet: true,
        VoucherRedeemSheet: true,
      },
    },
  })
}

describe('SplitPaySettleScreen settle isolation', () => {
  beforeEach(() => {
    onGreenCheck.mockReset()
    offerPaymentReceiptAfterSettle.mockReset()
    showToast.mockReset()
    remainingItemCount.value = 0
    onGreenCheck.mockResolvedValue({ remaining_cents: 0, payment_id: 77 })
    offerPaymentReceiptAfterSettle.mockResolvedValue(undefined)
  })

  it('labels green pay control Betrag when no open qty remains', async () => {
    remainingItemCount.value = 0
    const wrapper = mountSettleScreen()
    await flushPromises()

    const payBtn = wrapper.findAll('button').find((b) => b.text().includes('Betrag'))
    expect(payBtn).toBeTruthy()
    expect(payBtn!.text()).toMatch(/^Betrag\b/)
    expect(payBtn!.text()).not.toContain('Teilbetrag')
  })

  it('labels green pay control Teilbetrag when open qty remains below', async () => {
    remainingItemCount.value = 2
    const wrapper = mountSettleScreen()
    await flushPromises()

    const payBtn = wrapper.findAll('button').find((b) => b.text().includes('Teilbetrag'))
    expect(payBtn).toBeTruthy()
    expect(payBtn!.text()).toMatch(/^Teilbetrag\b/)
  })

  it('emits settled after full settle once receipt AfterSettle completes', async () => {
    remainingItemCount.value = 0
    const wrapper = mountSettleScreen()

    await flushPromises()
    const payBtn = wrapper.findAll('button').find((b) => b.text().includes('Betrag'))
    expect(payBtn).toBeTruthy()
    await payBtn!.trigger('click')
    await flushPromises()

    expect(offerPaymentReceiptAfterSettle).toHaveBeenCalledWith(
      expect.objectContaining({ paymentId: 77 }),
    )
    expect(wrapper.emitted('settled')).toBeTruthy()
    expect(showToast).toHaveBeenCalledWith('Abgerechnet.', 'ok')
  })
})
