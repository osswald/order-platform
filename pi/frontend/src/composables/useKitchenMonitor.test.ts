import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EdgeBundleEvent, KitchenOrderTicket, KitchenOrdersResponse } from '@/types/api'
import { useKitchenMonitor } from './useKitchenMonitor'

const apiMock = vi.fn()

vi.mock('@/api', () => ({
  api: (...args: unknown[]) => apiMock(...args),
}))

const eventFixture = {
  id: 1,
  name: 'Test',
  currency: 'CHF',
  payment_mode: 'pay_later',
  kitchen_monitors_enabled: true,
  configuration: {
    kitchen_monitors: [{ printer_appliance_id: 101, label: 'Grill', sort_order: 0 }],
  },
} as EdgeBundleEvent

describe('useKitchenMonitor', () => {
  beforeEach(() => {
    apiMock.mockReset()
  })

  it('loads orders for printer slug from route', async () => {
    const event = ref(eventFixture)
    const printerSlug = ref('grill')
    apiMock.mockResolvedValueOnce({
      orders: [
        { id: 1, ordered_at: '2026-01-01T12:00:00.000Z', lines: [], status: 'open' },
      ],
    } as unknown as KitchenOrdersResponse)

    const monitor = useKitchenMonitor({ event, printerSlug })
    await monitor.loadOrders()

    expect(monitor.selectedPrinter.value?.label).toBe('Grill')
    expect(apiMock).toHaveBeenCalledWith(
      '/v1/kitchen/orders?event_id=1&printer_appliance_id=101',
    )
  })

  it('posts partial print payload', async () => {
    const event = ref(eventFixture)
    const printerSlug = ref('grill')
    apiMock
      .mockResolvedValueOnce({ print_job_id: 9, ticket_status: 'partial' })
      .mockResolvedValueOnce({ orders: [] } as unknown as KitchenOrdersResponse)

    const monitor = useKitchenMonitor({ event, printerSlug })
    await monitor.printPartial({ id: 7, lines: [], status: 'open' } as unknown as KitchenOrderTicket, [
      { line_id: 3, qty: 2 },
    ])

    expect(apiMock).toHaveBeenCalledWith('/v1/kitchen/tickets/7/print-partial', {
      method: 'POST',
      body: JSON.stringify({ lines: [{ line_id: 3, qty: 2 }] }),
    })
  })

  it('flags unknown printer slug', async () => {
    const event = ref(eventFixture)
    const printerSlug = ref('bar')
    const monitor = useKitchenMonitor({ event, printerSlug })
    expect(monitor.unknownPrinterSlug.value).toBe(true)
  })
})
