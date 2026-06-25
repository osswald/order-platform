import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import type { EdgeBundleEvent } from '@/types/api'

vi.mock('../store', () => ({
  additionsSignature: (adds: unknown) => JSON.stringify(adds || []),
  articleName: (id: number) => `Artikel ${id}`,
  showToast: vi.fn(),
}))

vi.mock('../api', () => ({
  api: vi.fn(),
}))

vi.mock('../utils/paymentTypes', () => ({
  buildPayment: vi.fn((cents) => [{ type: 'instant', amount_cents: cents }]),
}))

vi.mock('../utils/resolvePayment', () => ({
  resolvePaymentsForAmount: vi.fn(async (_ev, cents) => [{ type: 'cash', amount_cents: cents }]),
}))

import { api } from '@/api'
import { useSplitPay } from './useSplitPay'

const summaryFixture = {
  total_cents: 900,
  line_groups: [
    {
      article_id: 10,
      note: '',
      additions: [],
      total_qty: 3,
      unit_cents: 500,
      line_total_cents: 900,
    },
  ],
}

function createSplitPay(overrides: Record<string, unknown> = {}) {
  const event = ref({
    id: 1,
    articles: { 10: { id: 10, name: 'Bier' } },
  } as unknown as EdgeBundleEvent)
  const loadSummary = vi.fn().mockResolvedValue(summaryFixture)
  return {
    event,
    loadSummary,
    splitPay: useSplitPay({
      event,
      paymentMode: ref('pay_later'),
      loadSummary,
      settlePartialPath: () => '/v1/tables/5/settle-partial',
      ...overrides,
    }),
  }
}

describe('useSplitPay', () => {
  beforeEach(() => {
    vi.mocked(api).mockReset()
  })

  it('initializes groups from summary and computes basket totals', async () => {
    const { splitPay, loadSummary } = createSplitPay()
    const { groups, rawBasketCents, basketItemCount, topGroups, reload } = splitPay

    await reload()

    expect(loadSummary).toHaveBeenCalled()
    expect(groups.value).toHaveLength(1)
    expect(groups.value[0].basketQty).toBe(3)
    expect(rawBasketCents.value).toBe(900)
    expect(basketItemCount.value).toBe(3)
    expect(topGroups.value).toHaveLength(1)
  })

  it('moveAllToBottom clears basket and moveAllToTop restores qty', async () => {
    const { splitPay } = createSplitPay()
    const { groups, rawBasketCents, moveAllToBottom, moveAllToTop, reload } = splitPay

    await reload()
    moveAllToBottom()
    expect(rawBasketCents.value).toBe(0)

    moveAllToTop()
    expect(rawBasketCents.value).toBe(900)
    expect(groups.value[0].basketQty).toBe(3)
  })

  it('selectionsPayload includes only top basket lines', async () => {
    const { splitPay } = createSplitPay()
    const { groups, bumpBasket, selectionsPayload, reload } = splitPay

    await reload()
    bumpBasket(groups.value[0], -2)
    expect(selectionsPayload()).toEqual([
      {
        article_id: 10,
        note: '',
        qty: 1,
        additions: [],
      },
    ])
  })

  it('applies voucher credit to basketCents', async () => {
    const voucherRedemptions = ref([{ applied_cents: 200 }])
    const { splitPay } = createSplitPay({ voucherRedemptions })
    const { basketCents, voucherCreditCents, reload } = splitPay

    await reload()

    expect(voucherCreditCents.value).toBe(200)
    expect(basketCents.value).toBe(700)
  })

  it('onGreenCheck settles when payments resolve', async () => {
    vi.mocked(api).mockResolvedValue({ remaining_cents: 0 })
    const onFullySettled = vi.fn()
    const { splitPay } = createSplitPay()
    const { reload, onGreenCheck } = splitPay
    await reload()
    await onGreenCheck(onFullySettled)
    expect(api).toHaveBeenCalled()
    expect(onFullySettled).toHaveBeenCalled()
  })
})
