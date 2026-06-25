import { ref, computed } from 'vue'
import type { DiscountIn, LineAdditionIn } from '@/types/api'
import type { CartLine, ToastState, RegisterSession, WaiterSession } from '@/types/cart'
import { cartLineLabelForEvent, voucherDefinitionByUuid } from '@/utils/bundleHelpers'
import {
  lineGrossCents,
  normalizeDiscount,
  orderSubtotalCents,
  orderTotalCents,
} from '@/utils/money'
import {
  activeTableNumber,
  persistRegisterSession,
  persistWaiterSession,
  REGISTER_SESSION_KEY,
  registerSession,
  selectedEventId,
  WAITER_SESSION_KEY,
  waiter,
} from './sessions'
import { cartLines, clearCart, orderDiscount } from './cart'
import { bundle, getArticle, selectedEvent, setAfterBundleLoaded } from './bundle'

export { cartLines, clearCart, orderDiscount, setOrderDiscount } from './cart'
export {
  activeTableNumber,
  persistRegisterSession,
  persistWaiterSession,
  registerSession,
  selectedEventId,
  waiter,
} from './sessions'
export {
  articleName,
  bundle,
  bundleReady,
  busy,
  getArticle,
  lastSyncAt,
  patchEventArticles,
  refreshBundle,
  selectedEvent,
  stockArticlesForEvent,
  syncError,
} from './bundle'
export {
  adminRequiresPin,
  adminUnlocked,
  clearAdminSession,
  setAdminUnlocked,
  verifyAdminPin,
} from './admin'

export const toast = ref<ToastState | null>(null)

let toastTimer: ReturnType<typeof setTimeout> | null = null

export function showToast(message: string, type: ToastState['type'] = 'ok'): void {
  toast.value = { message, type }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value = null
    toastTimer = null
  }, 4000)
}

setAfterBundleLoaded(() => {
  validateWaiterSession()
  validateRegisterSession()
})

export function validateWaiterSession(): void {
  if (!waiter.value) return
  const b = bundle.value
  if (!b?.events) return
  const eventId = selectedEventId.value
  if (eventId == null) {
    setWaiter(null)
    return
  }
  const ev = b.events.find((e) => Number(e.id) === Number(eventId))
  if (!ev) {
    setWaiter(null)
    selectedEventId.value = null
    return
  }
  const configured = (ev.configuration?.event_waiters || []).find(
    (x) => String(x.uuid) === String(waiter.value!.uuid),
  )
  if (!configured) {
    setWaiter(null)
    selectedEventId.value = null
    return
  }
  waiter.value = { uuid: String(configured.uuid), name: String(configured.name) }
  persistWaiterSession({ eventId: Number(eventId), uuid: String(configured.uuid), name: String(configured.name) })
}

export function setWaiter(w: WaiterSession | null): void {
  waiter.value = w
  if (w != null) setRegisterSession(null)
  clearCart()
  activeTableNumber.value = null
  if (typeof localStorage === 'undefined') return
  if (w == null) {
    localStorage.removeItem(WAITER_SESSION_KEY)
  } else {
    persistWaiterSession({
      eventId: selectedEventId.value!,
      uuid: w.uuid,
      name: w.name,
    })
  }
}

export function validateRegisterSession(): void {
  if (!registerSession.value) return
  const b = bundle.value
  if (!b?.events) return
  const eventId = selectedEventId.value
  if (eventId == null) {
    setRegisterSession(null)
    return
  }
  const ev = b.events.find((e) => Number(e.id) === Number(eventId))
  if (!ev) {
    setRegisterSession(null)
    selectedEventId.value = null
    return
  }
  const configured = (ev.configuration?.cash_registers || []).find(
    (x) => String(x.uuid) === String(registerSession.value!.uuid),
  )
  if (!configured) {
    setRegisterSession(null)
    return
  }
  registerSession.value = { uuid: String(configured.uuid), name: String(configured.name) }
  persistRegisterSession({
    eventId: Number(eventId),
    uuid: String(configured.uuid),
    name: String(configured.name),
  })
}

export function setRegisterSession(r: RegisterSession | null): void {
  registerSession.value = r
  if (r != null) setWaiter(null)
  clearCart()
  activeTableNumber.value = null
  if (typeof localStorage === 'undefined') return
  if (r == null) {
    localStorage.removeItem(REGISTER_SESSION_KEY)
  } else {
    persistRegisterSession({
      eventId: selectedEventId.value!,
      uuid: r.uuid,
      name: r.name,
    })
  }
}

export function cartQtyForArticle(articleId: number | string, excludeLineId: string | null = null): number {
  const aid = Number(articleId)
  return cartLines.value
    .filter((l) => l.article_id === aid && l.lineId !== excludeLineId)
    .reduce((s, l) => s + l.qty, 0)
}

export function cartQtyForAddition(additionId: number | string, excludeLineId: string | null = null): number {
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

export function availableAdditionQty(
  additionId: number | string,
  excludeLineId: string | null = null,
): number | null {
  const a = getArticle(additionId)
  if (!a?.monitor_stock) return null
  const stock = a.in_stock ?? 0
  return Math.max(0, stock - cartQtyForAddition(additionId, excludeLineId))
}

export function additionsSignature(additions: LineAdditionIn[] | null | undefined): string {
  const list = (additions || []).map((a) => ({
    article_id: Number(a.article_id),
    qty: Math.max(1, Number(a.qty) || 1),
  }))
  list.sort((x, y) => x.article_id - y.article_id)
  return JSON.stringify(list)
}

export function discountSignature(discount: DiscountIn | null | undefined): string {
  const d = normalizeDiscount(discount)
  return d ? JSON.stringify(d) : ''
}

/** Remaining units that can still be added to the cart (null = unlimited). */
export function availableQty(articleId: number | string, excludeLineId: string | null = null): number | null {
  const a = getArticle(articleId)
  if (!a?.monitor_stock) return null
  const stock = a.in_stock ?? 0
  return Math.max(0, stock - cartQtyForArticle(articleId, excludeLineId))
}

export interface AddCartLineInput {
  article_id: number | string
  qty?: number
  station_uuid?: string | null
  note?: string
  additions?: LineAdditionIn[]
  excludeLineId?: string | null
}

export function addCartLine({
  article_id,
  qty,
  station_uuid,
  note = '',
  additions = [],
  excludeLineId = null,
}: AddCartLineInput): boolean {
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
  const discountSig = discountSignature(undefined)
  const existing = cartLines.value.find(
    (l) =>
      l.article_id === aid &&
      l.station_uuid === su &&
      (l.note || '') === noteStr &&
      additionsSignature(l.additions) === sig &&
      discountSignature(l.discount) === discountSig,
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

export function removeCartLine(lineId: string): void {
  cartLines.value = cartLines.value.filter((l) => l.lineId !== lineId)
}

export function decrementCartLine(lineId: string): void {
  const l = cartLines.value.find((x) => x.lineId === lineId)
  if (!l) return
  if (l.qty <= 1) removeCartLine(lineId)
  else l.qty -= 1
}

export function updateCartLine(lineId: string, patch: Partial<CartLine>): void {
  cartLines.value = cartLines.value.map((l) => {
    if (l.lineId !== lineId) return l
    const next = { ...l, ...patch }
    if ('discount' in patch && patch.discount === undefined) {
      delete next.discount
    }
    return next
  })
}

export const cartCount = computed(() => cartLines.value.reduce((s, l) => s + l.qty, 0))

export const cartSubtotalCents = computed(() => {
  const ev = selectedEvent.value
  const arts = ev?.articles || {}
  return orderSubtotalCents(cartLines.value, arts, ev)
})

export const cartGrossCents = computed(() => {
  const ev = selectedEvent.value
  const arts = ev?.articles || {}
  return cartLines.value.reduce((s, l) => s + lineGrossCents(l, arts, ev), 0)
})

export const cartTotalCents = computed(() => {
  const ev = selectedEvent.value
  const arts = ev?.articles || {}
  return orderTotalCents(cartLines.value, orderDiscount.value, arts, ev)
})

export const cartDiscountCents = computed(() =>
  Math.max(0, cartGrossCents.value - cartTotalCents.value),
)

export interface AddVoucherCartLineInput {
  voucher_definition_uuid: string
  qty?: number
  unit_cents?: number | null
}

export function addVoucherCartLine({
  voucher_definition_uuid,
  qty = 1,
  unit_cents = null,
}: AddVoucherCartLineInput): boolean {
  const ev = selectedEvent.value
  if (!ev) {
    showToast('Kein Event geladen', 'err')
    return false
  }
  const vd = voucherDefinitionByUuid(ev, voucher_definition_uuid)
  if (!vd || vd.kind !== 'fixed_amount') {
    showToast('Unbekannter Gutschein', 'err')
    return false
  }
  const uc = unit_cents != null ? Number(unit_cents) : Number(vd.value_cents) || 0
  const existing = cartLines.value.find(
    (l) => l.kind === 'voucher_sale' && l.voucher_definition_uuid === vd.uuid,
  )
  const addQty = Math.max(1, Number(qty) || 1)
  if (existing) {
    existing.qty += addQty
    return true
  }
  cartLines.value.push({
    lineId: `V-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    kind: 'voucher_sale',
    voucher_definition_uuid: String(vd.uuid),
    qty: addQty,
    unit_cents: uc,
  })
  return true
}

export function cartLineLabel(line: CartLine): string {
  return cartLineLabelForEvent(line, selectedEvent.value)
}
