import { describe, expect, it, vi } from 'vitest'
import { validateCartStockBeforeSubmit } from './validateCartStock'

vi.mock('@/api/client', () => ({
  apiJson: vi.fn(),
}))

import { apiJson } from '@/api/client'

describe('validateCartStockBeforeSubmit', () => {
  it('posts lines to validate-order endpoint', async () => {
    vi.mocked(apiJson).mockResolvedValue({ ok: true })
    await validateCartStockBeforeSubmit(1, [{ article_id: 10, qty: 2, additions: [] }])
    expect(apiJson).toHaveBeenCalledWith('/v1/stock/validate-order', {
      method: 'POST',
      body: JSON.stringify({
        event_id: 1,
        lines: [{ article_id: 10, qty: 2, additions: [] }],
      }),
    })
  })
})
