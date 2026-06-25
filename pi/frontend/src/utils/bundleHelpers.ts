import type {
  DiscountIn,
  EdgeBundleArticle,
  EdgeBundleEvent,
  EdgeBundleResponse,
} from '@/types/api'

export function getDefaultLayout(event: EdgeBundleEvent | null | undefined) {
  const layouts = event?.configuration?.app_layouts
  if (!Array.isArray(layouts) || !layouts.length) return null
  const def = layouts.find((l) => l.is_default)
  return def || layouts[0]
}

export function isArticleSellable(article: EdgeBundleArticle | null | undefined): boolean {
  if (!article) return false
  if (article.is_addition) return false
  if (article.sellable === false) return false
  return true
}

export function hasAdditions(article: EdgeBundleArticle | null | undefined): boolean {
  return Array.isArray(article?.additions) && article.additions.length > 0
}

/** Normalize additions like Pi edge API _normalize_additions. */
export function normalizeLineAdditions(
  additions: Array<{ article_id?: number | null; qty?: number | null }> | null | undefined,
) {
  const out: Array<{ article_id: number; qty: number }> = []
  for (const add of additions || []) {
    if (!add || add.article_id == null) continue
    out.push({
      article_id: Number(add.article_id),
      qty: Math.max(1, Number(add.qty) || 1),
    })
  }
  return out
}

export function lineIdentityKey(
  articleId: number | string,
  note = '',
  additions: Array<{ article_id: number; qty?: number }> | null = null,
): string {
  const items = normalizeLineAdditions(additions)
  items.sort((a, b) => a.article_id - b.article_id || a.qty - b.qty)
  const sig = JSON.stringify(items)
  return `${Number(articleId)}:${String(note || '')}:${sig}`
}

function discountKeyPart(discount: DiscountIn | null | undefined): string {
  if (!discount || typeof discount !== 'object') return ''
  const kind = String(discount.kind || '').toLowerCase()
  if (kind !== 'percent' && kind !== 'amount') return ''
  const value = Math.max(0, Number(discount.value) || 0)
  if (value <= 0) return ''
  if (kind === 'percent') return JSON.stringify({ kind, value: Math.min(100, value) })
  return JSON.stringify({ kind, value })
}

export function lineIdentityKeyFromItem(item: {
  article_id: number
  note?: string
  additions?: Array<{ article_id: number; qty?: number }>
  discount?: DiscountIn | null
}): string {
  const base = lineIdentityKey(item.article_id, item.note, item.additions)
  const dk = discountKeyPart(item.discount)
  return dk ? `${base}:${dk}` : base
}

export function lineAdditionLabels(
  line: { article_id: number; additions?: Array<{ article_id: number; qty?: number }> },
  articles: Record<string, EdgeBundleArticle> | null | undefined,
): Array<{ id: number; name: string }> {
  const base = articles?.[String(line.article_id)] || articles?.[line.article_id]
  const out: Array<{ id: number; name: string }> = []
  for (const add of line.additions || []) {
    const id = Number(add.article_id)
    let name = `#${id}`
    const fromLine = (base?.additions || []).find((x) => Number(x.article_id) === id)
    if (fromLine?.name) name = fromLine.name
    else {
      const a = articles?.[String(id)] || articles?.[id]
      if (a?.name) name = a.name
    }
    out.push({ id, name })
  }
  return out
}

export function maxAddQty(article: EdgeBundleArticle | null | undefined, cartQty = 0): number | null {
  if (!article?.monitor_stock) return null
  const stock = article.in_stock ?? 0
  return Math.max(0, stock - cartQty)
}

export function resolveStationUuidForArticle(
  event: EdgeBundleEvent | null | undefined,
  articleId: number | string,
): string | null {
  const stations = event?.configuration?.stations
  if (!Array.isArray(stations)) return null
  const id = Number(articleId)
  for (const st of stations) {
    const ids = (st.article_ids || []).map(Number)
    if (ids.includes(id) && st.uuid) return String(st.uuid)
  }
  return null
}

export function voucherDefinitionsForEvent(event: EdgeBundleEvent | null | undefined) {
  return event?.configuration?.voucher_definitions || []
}

export function voucherDefinitionByUuid(
  event: EdgeBundleEvent | null | undefined,
  uuid: string | null | undefined,
) {
  const key = String(uuid || '')
  return voucherDefinitionsForEvent(event).find((d) => String(d.uuid) === key) || null
}

export function cellVoucherUuids(cell: {
  voucher_definition_uuids?: string[] | null
  voucher_definition_uuid?: string | null
} | null | undefined): string[] {
  const list = cell?.voucher_definition_uuids
  if (Array.isArray(list) && list.length) {
    return list.map((x) => String(x).trim()).filter(Boolean)
  }
  const legacy = String(cell?.voucher_definition_uuid || '').trim()
  return legacy ? [legacy] : []
}

export function fixedAmountVouchersForCell(
  event: EdgeBundleEvent | null | undefined,
  cell: Parameters<typeof cellVoucherUuids>[0],
) {
  const out = []
  for (const vUuid of cellVoucherUuids(cell)) {
    const vd = voucherDefinitionByUuid(event, vUuid)
    if (vd && vd.kind === 'fixed_amount') out.push(vd)
  }
  return out
}

export function cartLineLabelForEvent(
  line: {
    kind?: string
    voucher_definition_uuid?: string
    article_id?: number
  } | null | undefined,
  event: EdgeBundleEvent | null | undefined,
): string {
  if (line?.kind === 'voucher_sale') {
    const vd = voucherDefinitionByUuid(event, line.voucher_definition_uuid)
    return typeof vd?.name === 'string' && vd.name ? vd.name : 'Gutschein'
  }
  const arts = event?.articles || {}
  const id = line?.article_id
  const a = id != null ? arts[String(id)] ?? arts[id as unknown as string] : undefined
  return a?.name || `Artikel #${id}`
}

export function articlesForIds(event: EdgeBundleEvent | null | undefined, articleIds: number[]) {
  const arts = event?.articles || {}
  const out: Array<EdgeBundleArticle & { id: number }> = []
  for (const raw of articleIds || []) {
    const id = Number(raw)
    const a = arts[String(id)] || arts[id]
    if (a && isArticleSellable(a)) out.push({ ...a, id })
  }
  return out
}

export function printerHostConfigured(
  event: EdgeBundleEvent | null | undefined,
  uuid: string,
): boolean {
  const hosts = event?.printer_hosts || {}
  const raw = hosts[String(uuid)]
  if (raw == null) return false
  if (typeof raw === 'string') {
    const host = raw.split(':')[0]?.trim()
    return Boolean(host)
  }
  if (typeof raw === 'object' && raw !== null) {
    return Boolean(String((raw as { host?: string }).host || '').trim())
  }
  return false
}

export function receiptPrintTargets(event: EdgeBundleEvent | null | undefined) {
  const out: Array<{ uuid: string; label: string; kind: 'station' | 'register' }> = []
  for (const st of event?.configuration?.stations || []) {
    const uuid = String(st.uuid || '').trim()
    if (!uuid || !printerHostConfigured(event, uuid)) continue
    out.push({ uuid, label: st.name || uuid, kind: 'station' })
  }
  for (const reg of event?.configuration?.cash_registers || []) {
    const uuid = String(reg.uuid || '').trim()
    if (!uuid || !printerHostConfigured(event, uuid)) continue
    const name = reg.name || uuid
    out.push({ uuid, label: `Kasse: ${name}`, kind: 'register' })
  }
  return out.sort((a, b) => a.label.localeCompare(b.label, 'de'))
}

export function positionCommentsEnabled(bundle: EdgeBundleResponse | null | undefined): boolean {
  return Boolean(bundle?.position_comments_enabled)
}

export function positionCommentPresets(bundle: EdgeBundleResponse | null | undefined) {
  return Array.isArray(bundle?.position_comment_presets) ? bundle.position_comment_presets : []
}
