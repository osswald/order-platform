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
