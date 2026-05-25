/**
 * @param {object} event - edge event bundle item
 * @returns {object | null} layout or null
 */
export function getDefaultLayout(event) {
  const layouts = event?.configuration?.app_layouts
  if (!Array.isArray(layouts) || !layouts.length) return null
  const def = layouts.find((l) => l.is_default)
  return def || layouts[0]
}

export function isArticleSellable(article) {
  if (!article) return false
  if (article.is_addition) return false
  if (article.sellable === false) return false
  return true
}

export function hasAdditions(article) {
  return Array.isArray(article?.additions) && article.additions.length > 0
}

/** Normalize additions like Pi edge API _normalize_additions. */
export function normalizeLineAdditions(additions) {
  const out = []
  for (const add of additions || []) {
    if (!add || add.article_id == null) continue
    out.push({
      article_id: Number(add.article_id),
      qty: Math.max(1, Number(add.qty) || 1),
    })
  }
  return out
}

/**
 * Stable key for matching order lines / split-pay groups (matches backend _additions_signature).
 * @param {number} articleId
 * @param {string} [note]
 * @param {Array<{ article_id: number, qty?: number }>} [additions]
 */
export function lineIdentityKey(articleId, note = '', additions = null) {
  const items = normalizeLineAdditions(additions)
  items.sort((a, b) => a.article_id - b.article_id || a.qty - b.qty)
  const sig = JSON.stringify(items)
  return `${Number(articleId)}:${String(note || '')}:${sig}`
}

/** @param {{ article_id: number, note?: string, additions?: Array }} item */
export function lineIdentityKeyFromItem(item) {
  return lineIdentityKey(item.article_id, item.note, item.additions)
}

/**
 * @param {{ article_id: number, additions?: Array<{ article_id: number, qty?: number }> }} line
 * @param {object} articles - event.articles map
 * @returns {Array<{ id: number, name: string }>}
 */
export function lineAdditionLabels(line, articles) {
  const base = articles?.[String(line.article_id)] || articles?.[line.article_id]
  const out = []
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

/** @param {object} article
 * @param {number} cartQty - qty already in cart for this article
 */
export function maxAddQty(article, cartQty = 0) {
  if (!article?.monitor_stock) return null
  const stock = article.in_stock ?? 0
  return Math.max(0, stock - cartQty)
}

/**
 * First station whose article_ids contains articleId.
 * @param {object} event
 * @param {number} articleId
 * @returns {string | null} station uuid
 */
export function resolveStationUuidForArticle(event, articleId) {
  const stations = event?.configuration?.stations
  if (!Array.isArray(stations)) return null
  const id = Number(articleId)
  for (const st of stations) {
    const ids = (st.article_ids || []).map(Number)
    if (ids.includes(id) && st.uuid) return String(st.uuid)
  }
  return null
}

/**
 * @param {object} event
 * @param {number[]} articleIds
 * @returns {object[]} article objects from event.articles
 */
export function voucherDefinitionsForEvent(event) {
  return event?.configuration?.voucher_definitions || []
}

export function voucherDefinitionByUuid(event, uuid) {
  const key = String(uuid || '')
  return voucherDefinitionsForEvent(event).find((d) => String(d.uuid) === key) || null
}

/** Voucher uuids on a layout cell (plural list + legacy single field). */
export function cellVoucherUuids(cell) {
  const list = cell?.voucher_definition_uuids
  if (Array.isArray(list) && list.length) {
    return list.map((x) => String(x).trim()).filter(Boolean)
  }
  const legacy = String(cell?.voucher_definition_uuid || '').trim()
  return legacy ? [legacy] : []
}

/** fixed_amount voucher definitions referenced by a layout cell. */
export function fixedAmountVouchersForCell(event, cell) {
  const out = []
  for (const vUuid of cellVoucherUuids(cell)) {
    const vd = voucherDefinitionByUuid(event, vUuid)
    if (vd && vd.kind === 'fixed_amount') out.push(vd)
  }
  return out
}

/** Cart / customer-display line title (voucher_sale + articles). */
export function cartLineLabelForEvent(line, event) {
  if (line?.kind === 'voucher_sale') {
    const vd = voucherDefinitionByUuid(event, line.voucher_definition_uuid)
    return vd?.name || 'Gutschein'
  }
  const arts = event?.articles || {}
  const id = line?.article_id
  const a = arts[String(id)] || arts[id]
  return a?.name || `Artikel #${id}`
}

export function articlesForIds(event, articleIds) {
  const arts = event?.articles || {}
  const out = []
  for (const raw of articleIds || []) {
    const id = Number(raw)
    const a = arts[String(id)] || arts[id]
    if (a && isArticleSellable(a)) out.push({ ...a, id })
  }
  return out
}
