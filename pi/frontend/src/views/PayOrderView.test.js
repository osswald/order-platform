import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'

const push = vi.fn()
const replace = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: '42' },
    query: { table: '5', total_cents: '500' },
  }),
  useRouter: () => ({ push, replace }),
}))

vi.mock('../api', () => ({
  api: vi.fn(),
}))

vi.mock('../composables/useCart', () => ({
  useCart: () => ({
    activeTableNumber: ref('5'),
    articleName: (id) => `Artikel ${id}`,
  }),
}))

vi.mock('../composables/useEventContext', () => ({
  useEventContext: () => ({
    event: ref({
      id: 1,
      articles: { 10: { id: 10, name: 'Bier', price: 5 } },
    }),
    showToast: vi.fn(),
  }),
}))

vi.mock('../utils/resolvePayment', () => ({
  resolvePaymentsForAmount: vi.fn(async () => [{ type: 'cash', amount_cents: 500 }]),
}))

vi.mock('../utils/paymentReceiptPrompt', () => ({
  offerPaymentReceipt: vi.fn(),
}))

import { api } from '../api'
import PayOrderView from './PayOrderView.vue'

describe('PayOrderView', () => {
  beforeEach(() => {
    vi.mocked(api).mockReset()
    push.mockReset()
    replace.mockReset()
    vi.mocked(api).mockResolvedValue({
      open_orders: [
        {
          local_order_id: 42,
          line_total_cents: 500,
          lines: [{ article_id: 10, qty: 1, unit_cents: 500 }],
        },
      ],
    })
  })

  it('loads order lines and shows payment total', async () => {
    const wrapper = mount(PayOrderView, {
      global: {
        stubs: {
          MoneyKeypad: {
            template: '<div data-testid="keypad" />',
            props: ['modelValue'],
          },
        },
      },
    })

    await flushPromises()

    expect(api).toHaveBeenCalledWith('/v1/tables/5?event_id=1')
    expect(wrapper.text()).toContain('Zu zahlen:')
    expect(wrapper.text()).toContain('5.00')
    expect(wrapper.find('[data-testid="keypad"]').exists()).toBe(true)
  })
})
