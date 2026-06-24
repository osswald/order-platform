import { ref, computed } from 'vue'
import { additionsSignature, articleName, showToast } from '../store'
import { api } from '../api'
import { formatAmount } from '../utils/money'
import { lineAdditionLabels } from '../utils/bundleHelpers'
import { buildPayment } from '../utils/paymentTypes'
import { resolvePaymentsForAmount } from '../utils/resolvePayment'
import {
  basketCentsAfterVoucher,
  sumGroupBasketCents,
  sumVoucherCreditCents,
} from '../utils/splitPay'

export function useSplitPay({
  event,
  paymentMode,
  loadSummary,
  settlePartialPath,
  voucherRedemptions = ref([]),
}) {
  const summary = ref(null)
  const groups = ref([])
  const loading = ref(true)
  const paying = ref(false)
  const qtyModalOpen = ref(false)
  const qtyModalGroup = ref(null)

  const totalCents = computed(() => summary.value?.total_cents || 0)

  const rawBasketCents = computed(() => sumGroupBasketCents(groups.value))
  const voucherCreditCents = computed(() => sumVoucherCreditCents(voucherRedemptions.value))
  const basketCents = computed(() =>
    basketCentsAfterVoucher(rawBasketCents.value, voucherCreditCents.value),
  )
  const restCents = computed(() => Math.max(0, totalCents.value - rawBasketCents.value))
  const basketItemCount = computed(() => groups.value.reduce((s, g) => s + g.basketQty, 0))
  const remainingItemCount = computed(() =>
    groups.value.reduce((s, g) => s + (g.totalQty - g.basketQty), 0),
  )
  const topGroups = computed(() => groups.value.filter((g) => g.basketQty > 0))
  const bottomGroups = computed(() => groups.value.filter((g) => g.basketQty < g.totalQty))

  function lineKey(articleId, note, additions) {
    return `${articleId}:${note || ''}:${additionsSignature(additions || [])}`
  }

  function initGroups(data) {
    const arts = event.value?.articles || {}
    const lg = data?.line_groups || []
    groups.value = lg.map((g) => {
      const additions = g.additions || []
      const discount = g.discount || null
      const line = { article_id: g.article_id, additions, discount, qty: 1 }
      const discKey = discount ? JSON.stringify(discount) : ''
      return {
        key: `${lineKey(g.article_id, g.note, additions)}:${discKey}`,
        article_id: g.article_id,
        note: g.note || '',
        additions,
        discount,
        totalQty: g.total_qty,
        unitCents: g.unit_cents,
        lineTotalCents: g.line_total_cents ?? 0,
        basketQty: g.total_qty,
        name: articleName(g.article_id),
        additionLabels: lineAdditionLabels(line, arts),
      }
    })
  }

  function moveAllToBottom() {
    for (const g of groups.value) g.basketQty = 0
  }

  function moveAllToTop() {
    for (const g of groups.value) g.basketQty = g.totalQty
  }

  function bumpBasket(g, delta) {
    g.basketQty = Math.min(g.totalQty, Math.max(0, g.basketQty + delta))
  }

  function openQtyModal(g) {
    qtyModalGroup.value = g
    qtyModalOpen.value = true
  }

  function onQtyConfirm(n) {
    if (qtyModalGroup.value) {
      const g = qtyModalGroup.value
      g.basketQty = Math.min(g.totalQty, Math.max(0, Number(n) || 0))
    }
    qtyModalOpen.value = false
  }

  function selectionsPayload() {
    return topGroups.value.map((g) => {
      const row = {
        article_id: g.article_id,
        note: g.note,
        qty: g.basketQty,
        additions: (g.additions || []).map((a) => ({
          article_id: a.article_id,
          qty: a.qty ?? 1,
        })),
      }
      if (g.discount) row.discount = g.discount
      return row
    })
  }

  async function paymentsForAmount(cents) {
    if (paymentMode.value === 'instant') {
      return buildPayment(cents, 'instant')
    }
    return resolvePaymentsForAmount(event.value, cents)
  }

  async function reload() {
    const data = await loadSummary()
    summary.value = data
    initGroups(data)
    return data
  }

  async function settlePartial(payments, onFullySettled) {
    paying.value = true
    try {
      const res = await api(settlePartialPath(), {
        method: 'POST',
        body: JSON.stringify({
          event_id: event.value.id,
          payments,
          selections: selectionsPayload(),
          voucher_redemptions: (voucherRedemptions.value || []).map((r) => ({
            voucher_definition_uuid: r.voucher_definition_uuid,
            article_id: r.article_id,
            note: r.note || '',
            qty: r.qty || 1,
            additions: (r.additions || []).map((a) => ({
              article_id: a.article_id,
              qty: a.qty ?? 1,
            })),
          })),
        }),
      })
      voucherRedemptions.value = []
      if (res.remaining_cents <= 0) {
        onFullySettled?.()
        return res
      }
      showToast(`Teilbetrag bezahlt. Rest: ${formatAmount(res.remaining_cents)}`, 'ok')
      await reload()
      return res
    } finally {
      paying.value = false
    }
  }

  async function onGreenCheck(onFullySettled) {
    if (!rawBasketCents.value) return
    let payments
    try {
      payments = await paymentsForAmount(basketCents.value)
    } catch (e) {
      if (e?.message !== 'cancelled') {
        showToast(e?.message || 'Zahlung abgebrochen.', 'err')
      }
      return
    }
    return settlePartial(payments, onFullySettled)
  }

  return {
    summary,
    groups,
    loading,
    paying,
    qtyModalOpen,
    qtyModalGroup,
    totalCents,
    rawBasketCents,
    voucherCreditCents,
    basketCents,
    voucherRedemptions,
    restCents,
    basketItemCount,
    remainingItemCount,
    topGroups,
    bottomGroups,
    moveAllToBottom,
    moveAllToTop,
    bumpBasket,
    openQtyModal,
    onQtyConfirm,
    selectionsPayload,
    reload,
    onGreenCheck,
  }
}
