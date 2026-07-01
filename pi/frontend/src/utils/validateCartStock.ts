import { apiJson } from '@/api/client'

export interface StockValidateLine {
  article_id: number
  qty: number
  additions?: { article_id: number; qty: number }[]
}

export async function validateCartStockBeforeSubmit(
  eventId: number,
  lines: StockValidateLine[],
): Promise<void> {
  await apiJson('/v1/stock/validate-order', {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId, lines }),
  })
}
