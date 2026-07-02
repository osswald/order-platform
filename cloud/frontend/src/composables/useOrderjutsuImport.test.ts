import { describe, expect, it, vi } from 'vitest'
import { useOrderjutsuImport } from './useOrderjutsuImport'

vi.mock('@/api', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '@/api'

describe('useOrderjutsuImport', () => {
  it('sends preview requests as JSON objects', async () => {
    vi.mocked(apiJson).mockResolvedValue({
      event: {
        name: 'Test',
        start: '2025-06-01T00:00:00Z',
        end: '2025-08-02T08:17:27Z',
        currency: 'CHF',
        currency_matches_org: true,
      },
      products: [],
      cashiers: [],
      stations: [],
      layouts: [],
      product_extras: [],
      stock_candidates: [],
      vouchers: [],
      has_ingredients: false,
      ingredients_enabled: false,
      will_enable_ingredients: false,
      ingredient_matches: [],
      recipe_rows: [],
      has_vouchers: false,
      has_cash_registers: false,
      warnings: [],
    })

    const { loadPreview } = useOrderjutsuImport(() => 1)
    const file = new File([JSON.stringify({ label: 'Test event' })], 'event.json', {
      type: 'application/json',
    })

    await loadPreview(file)

    expect(apiJson).toHaveBeenCalledWith('/events/import/orderjutsu/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ organisation_id: 1, payload: { label: 'Test event' } }),
    })

    const parsed = JSON.parse(String(vi.mocked(apiJson).mock.calls[0]?.[1]?.body))
    expect(parsed).toEqual({ organisation_id: 1, payload: { label: 'Test event' } })
  })
})
