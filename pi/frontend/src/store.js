import { ref, computed } from 'vue'
import { api } from './api'
import { lineTotalCents } from './utils/money'

/** @type {import('vue').Ref<object | null>} */
export const bundle = ref(null)
export const lastSyncAt = ref(null)
export const syncError = ref('')
export const busy = ref(false)

export const selectedEventId = ref(null)
/** @type {import('vue').Ref<{ id: number, name: string } | null>} */
export const waiter = ref(null)
export const activeTableNumber = ref(null)

/** @type {import('vue').Ref<Array<{ lineId: string, article_id: number, qty: number, station_uuid: string | null, note: string }>>} */
export const cartLines = ref([])

/** @type {import('vue').Ref<{ message: string, type: 'ok' | 'err' } | null>} */
export const toast = ref(null)

let toastTimer = null
export function showToast(message, type = 'ok') {
  toast.value = { message, type }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = null
    toastTimer = null
  }, 4000)
}

export const selectedEvent = computed(() => {
  const b = bundle.value
  const id = selectedEventId.value
  if (!b?.events || id == null) return null
  return b.events.find((e) => Number(e.id) === Number(id)) || null
})

export function clearCart() {
  cartLines.value = []
}

export function setWaiter(w) {
  waiter.value = w
  clearCart()
  activeTableNumber.value = null
}

export function getArticle(articleId) {
  const ev = selectedEvent.value
  if (!ev?.articles) return null
  return ev.articles[String(articleId)] || ev.articles[articleId] || null
}

export function cartQtyForArticle(articleId, excludeLineId = null) {
  const aid = Number(articleId)
  return cartLines.value
    .filter((l) => l.article_id === aid && l.lineId !== excludeLineId)
    .reduce((s, l) => s + l.qty, 0)
}

export function cartQtyForAddition(additionId, excludeLineId = null) {
  const aid = Number(additionId)
  let total = 0
  for (const l of cartLines.value) {
    if (excludeLineId && l.lineId === excludeLineId) continue
    for (const add of l.additions || []) {
      if (Number(add.article_id) === aid) {
        total += l.qty * Math.max(1, Number(add.qty) || 1)
      }
    }
  }
  return total
}

export function availableAdditionQty(additionId, excludeLineId = null) {
  const a = getArticle(additionId)
  if (!a?.monitor_stock) return null
  const stock = a.in_stock ?? 0
  return Math.max(0, stock - cartQtyForAddition(additionId, excludeLineId))
}

export function additionsSignature(additions) {
  const list = (additions || []).map((a) => ({
    article_id: Number(a.article_id),
    qty: Math.max(1, Number(a.qty) || 1),
  }))
  list.sort((x, y) => x.article_id - y.article_id)
  return JSON.stringify(list)
}

/** Remaining units that can still be added to the cart (null = unlimited). */
export function availableQty(articleId, excludeLineId = null) {
  const a = getArticle(articleId)
  if (!a?.monitor_stock) return null
  const stock = a.in_stock ?? 0
  return Math.max(0, stock - cartQtyForArticle(articleId, excludeLineId))
}

export function patchEventArticles(eventId, articlesMap) {
  const b = bundle.value
  if (!b?.events || !articlesMap) return
  const eid = Number(eventId)
  for (const ev of b.events) {
    if (Number(ev.id) !== eid) continue
    const arts = ev.articles || {}
    for (const [key, patch] of Object.entries(articlesMap)) {
      const k = String(key)
      const existing = arts[k] || arts[Number(key)]
      if (existing) arts[k] = { ...existing, ...patch }
      else arts[k] = patch
    }
    for (const base of Object.values(arts)) {
      if (!base?.additions) continue
      for (const add of base.additions) {
        const src = arts[String(add.article_id)] || arts[add.article_id]
        if (!src) continue
        if ('in_stock' in src) add.in_stock = src.in_stock
        if ('sellable' in src) add.sellable = src.sellable
        if ('monitor_stock' in src) add.monitor_stock = src.monitor_stock
      }
    }
    ev.articles = arts
    break
  }
}

export function addCartLine({
  article_id,
  qty,
  station_uuid,
  note = '',
  additions = [],
  excludeLineId = null,
}) {
  const aid = Number(article_id)
  const su = station_uuid != null && String(station_uuid).trim() ? String(station_uuid).trim() : null
  const noteStr = String(note || '')
  const adds = (additions || []).map((a) => ({
    article_id: Number(a.article_id),
    qty: Math.max(1, Number(a.qty) || 1),
  }))
  let addQty = Math.max(1, Number(qty) || 1)
  const avail = availableQty(aid, excludeLineId)
  if (avail !== null) {
    if (avail < 1) {
      showToast('Ausverkauft', 'err')
      return false
    }
    if (addQty > avail) {
      showToast(`Nur noch ${avail} verfügbar`, 'err')
      addQty = avail
    }
  }
  for (const add of adds) {
    const a = getArticle(add.article_id)
    if (a?.sellable === false) {
      showToast(`${a.name || 'Zusatz'} ausverkauft`, 'err')
      return false
    }
    const addAvail = availableAdditionQty(add.article_id, excludeLineId)
    if (addAvail !== null && addAvail < add.qty * addQty) {
      const name = a?.name || `Zusatz #${add.article_id}`
      showToast(`Nur noch ${addAvail} von «${name}» verfügbar`, 'err')
      return false
    }
  }
  const sig = additionsSignature(adds)
  const existing = cartLines.value.find(
    (l) =>
      l.article_id === aid &&
      l.station_uuid === su &&
      (l.note || '') === noteStr &&
      additionsSignature(l.additions) === sig,
  )
  if (existing) {
    existing.qty += addQty
    return true
  }
  cartLines.value.push({
    lineId: `L-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    article_id: aid,
    qty: addQty,
    station_uuid: su,
    note: noteStr,
    additions: adds,
  })
  return true
}

export function removeCartLine(lineId) {
  cartLines.value = cartLines.value.filter((l) => l.lineId !== lineId)
}

export function decrementCartLine(lineId) {
  const l = cartLines.value.find((x) => x.lineId === lineId)
  if (!l) return
  if (l.qty <= 1) removeCartLine(lineId)
  else l.qty -= 1
}

export function updateCartLine(lineId, patch) {
  cartLines.value = cartLines.value.map((l) => (l.lineId === lineId ? { ...l, ...patch } : l))
}

export const cartCount = computed(() => cartLines.value.reduce((s, l) => s + l.qty, 0))

export const cartTotalCents = computed(() => {
  const ev = selectedEvent.value
  const arts = ev?.articles || {}
  return cartLines.value.reduce((s, l) => s + lineTotalCents(l, arts), 0)
})

export function bundleReady() {
  const b = bundle.value
  return Boolean(b && b.organisation_id != null)
}

export async function refreshBundle() {
  const m = await api('/v1/meta')
  lastSyncAt.value = m.last_sync_at || null
  if (!lastSyncAt.value) {
    bundle.value = null
    return 0
  }
  try {
    const b = await api('/v1/bundle')
    bundle.value = b
    return (b.events || []).length
  } catch {
    bundle.value = null
    return 0
  }
}

export function articleName(articleId) {
  const ev = selectedEvent.value
  const a = ev?.articles?.[String(articleId)] || ev?.articles?.[articleId]
  return a?.name || `Artikel #${articleId}`
}

const ADMIN_SESSION_KEY = 'pi_admin_unlocked'

export const adminUnlocked = ref(sessionStorage.getItem(ADMIN_SESSION_KEY) === '1')

export function setAdminUnlocked(ok) {
  adminUnlocked.value = ok
  if (ok) sessionStorage.setItem(ADMIN_SESSION_KEY, '1')
  else sessionStorage.removeItem(ADMIN_SESSION_KEY)
}

export function clearAdminSession() {
  setAdminUnlocked(false)
}

export function adminRequiresPin() {
  if (!bundleReady()) return false
  const hashes = bundle.value?.admin_pin_hashes
  return Array.isArray(hashes) && hashes.length > 0
}

export async function verifyAdminPin(pin) {
  await api('/v1/admin/verify', {
    method: 'POST',
    body: JSON.stringify({ pin }),
  })
  setAdminUnlocked(true)
}

export function stockArticlesForEvent(ev) {
  if (!ev?.articles) return []
  return Object.values(ev.articles)
    .filter((a) => a && a.monitor_stock)
    .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'de'))
}
