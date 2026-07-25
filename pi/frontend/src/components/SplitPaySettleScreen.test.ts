import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'

const { onGreenCheck, offerPaymentReceiptAfterSettle, showToast } = vi.hoisted(() => ({
  onGreenCheck: vi.fn(),
  offerPaymentReceiptAfterSettle: vi.fn(),
  showToast: vi.fn(),
}))

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
    remainingItemCount: ref(0),
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

describe('SplitPaySettleScreen settle isolation', () => {
  beforeEach(() => {
    onGreenCheck.mockReset()
    offerPaymentReceiptAfterSettle.mockReset()
    showToast.mockReset()
    onGreenCheck.mockResolvedValue({ remaining_cents: 0, payment_id: 77 })
    offerPaymentReceiptAfterSettle.mockResolvedValue(undefined)
  })

  it('emits settled after full settle once receipt AfterSettle completes', async () => {
    const wrapper = mount(SplitPaySettleScreen, {
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

    await flushPromises()
    const payBtn = wrapper.findAll('button').find((b) => b.text().includes('Teilbetrag'))
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
