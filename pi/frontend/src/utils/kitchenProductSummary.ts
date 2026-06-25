import { getDefaultLayout } from '@/utils/bundleHelpers'
import type { EdgeBundleEvent, KitchenOrderTicket, KitchenTicketLineEntry, OrderLineIn } from '@/types/api'

export interface KitchenProductBreakdown {
  label: string
  qty: number
}

export interface KitchenProductRow {
  key: string
  articleId: number
  name: string
  totalQty: number
  breakdown: KitchenProductBreakdown[]
  color: string | null
  sortKey: number
}

export interface KitchenProductSummary {
  articles: KitchenProductRow[]
  additions: KitchenProductRow[]
}

export function kitchenProductLocationShortLabel(label: string): string {
  const table = String(label || '').match(/^Tisch\s+(.+)$/i)
  if (table) return table[1]
  const pickup = String(label || '').match(/^Pickup\s+(.+)$/i)
  if (pickup) return pickup[1]
  return label
}

function orderLocationLabel(ticket: KitchenOrderTicket): string {
  if (ticket.pickup_code) return `Pickup ${ticket.pickup_code}`
  const table = ticket.table_number
  if (table != null && String(table).trim()) return `Tisch ${table}`
  return `Bestellung #${ticket.order_number || ticket.id}`
}

export function articleLayoutMeta(
  event: EdgeBundleEvent | null | undefined,
  articleId: number,
): { color: string | null; sortKey: number } {
  const layout = getDefaultLayout(event)
  const cells = Array.isArray(layout?.cells) ? layout.cells : []
  for (let idx = 0; idx < cells.length; idx += 1) {
    const cell = cells[idx]
    const ids = (cell?.article_ids || []).map(Number)
    if (ids.includes(Number(articleId))) {
      return {
        color: typeof cell?.color === 'string' ? cell.color : null,
        sortKey: Number(cell?.row) * 1000 + Number(cell?.col) + idx * 0.001,
      }
    }
  }
  return { color: null, sortKey: Number.MAX_SAFE_INTEGER }
}

function articleName(
  articleId: number,
  event: EdgeBundleEvent | null | undefined,
  fallback?: string | null,
): string {
  if (fallback) return fallback
  const article = event?.articles?.[String(articleId)] || event?.articles?.[articleId as unknown as string]
  return article?.name || `#${articleId}`
}

function lineArticleName(
  entry: KitchenTicketLineEntry,
  event: EdgeBundleEvent | null | undefined,
): string {
  const line = entry.line as OrderLineIn & { article_name?: string }
  return articleName(Number(line.article_id), event, line.article_name)
}

interface AggregateBucket {
  articleId: number
  name: string
  totalQty: number
  breakdown: Map<string, KitchenProductBreakdown>
}

function addQty(bucket: AggregateBucket, location: string, qty: number) {
  if (qty <= 0) return
  bucket.totalQty += qty
  const existing = bucket.breakdown.get(location)
  if (existing) existing.qty += qty
  else bucket.breakdown.set(location, { label: location, qty })
}

function sortBreakdown(rows: KitchenProductBreakdown[]): KitchenProductBreakdown[] {
  return [...rows].sort((a, b) => {
    const tableA = a.label.match(/^Tisch\s+(\d+)/i)
    const tableB = b.label.match(/^Tisch\s+(\d+)/i)
    if (tableA && tableB) return Number(tableA[1]) - Number(tableB[1])
    return a.label.localeCompare(b.label, 'de')
  })
}

function bucketToRow(
  key: string,
  bucket: AggregateBucket,
  event: EdgeBundleEvent | null | undefined,
): KitchenProductRow {
  const layout = articleLayoutMeta(event, bucket.articleId)
  return {
    key,
    articleId: bucket.articleId,
    name: bucket.name,
    totalQty: bucket.totalQty,
    breakdown: sortBreakdown([...bucket.breakdown.values()]),
    color: layout.color,
    sortKey: layout.sortKey,
  }
}

function sortRows(rows: KitchenProductRow[]): KitchenProductRow[] {
  return rows.sort((a, b) => a.name.localeCompare(b.name, 'de', { sensitivity: 'base' }))
}

export function buildKitchenProductSummary(
  orders: KitchenOrderTicket[],
  event: EdgeBundleEvent | null | undefined,
): KitchenProductSummary {
  const articles = new Map<string, AggregateBucket>()
  const additions = new Map<string, AggregateBucket>()

  for (const ticket of orders) {
    const location = orderLocationLabel(ticket)
    for (const entry of ticket.lines || []) {
      const line = entry.line as OrderLineIn
      const lineQty = Math.max(0, Number(entry.qty_remaining) || 0)
      if (lineQty <= 0) continue

      const articleId = Number(line.article_id)
      const articleKey = String(articleId)
      const articleBucket = articles.get(articleKey) || {
        articleId,
        name: lineArticleName(entry, event),
        totalQty: 0,
        breakdown: new Map<string, KitchenProductBreakdown>(),
      }
      addQty(articleBucket, location, lineQty)
      articles.set(articleKey, articleBucket)

      for (const add of line.additions || []) {
        const addId = Number(add.article_id)
        if (!Number.isFinite(addId)) continue
        const addQtyPerLine = Math.max(1, Number(add.qty) || 1)
        const totalAddQty = lineQty * addQtyPerLine
        const addKey = String(addId)
        const addBucket = additions.get(addKey) || {
          articleId: addId,
          name: articleName(addId, event, add.name),
          totalQty: 0,
          breakdown: new Map<string, KitchenProductBreakdown>(),
        }
        addQty(addBucket, location, totalAddQty)
        additions.set(addKey, addBucket)
      }
    }
  }

  return {
    articles: sortRows([...articles.entries()].map(([key, bucket]) => bucketToRow(key, bucket, event))),
    additions: sortRows([...additions.entries()].map(([key, bucket]) => bucketToRow(key, bucket, event))),
  }
}
