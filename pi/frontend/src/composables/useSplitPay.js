import { ref, computed } from 'vue'
import * as store from '../store'
import { api } from '../api'
import { formatAmount } from '../utils/money'
import { lineAdditionLabels } from '../utils/bundleHelpers'
import { buildPayment } from '../utils/paymentTypes'
import { pickPaymentType } from '../utils/pickPaymentType'

export function useSplitPay({ event, paymentMode, loadSummary, settlePartialPath }) {
  const summary = ref(null)
  const groups = ref([])
  const loading = ref(true)
  const paying = ref(false)
  const qtyModalOpen = ref(false)
  const qtyModalGroup = ref(null)

  const totalCents = computed(() => summary.value?.total_cents || 0)
  const basketCents = computed(() =>
    groups.value.reduce((s, g) => s + g.unitCents * g.basketQty, 0),
  )
  const restCents = computed(() => Math.max(0, totalCents.value - basketCents.value))
  const basketItemCount = computed(() => groups.value.reduce((s, g) => s + g.basketQty, 0))
  const remainingItemCount = computed(() =>
    groups.value.reduce((s, g) => s + (g.totalQty - g.basketQty), 0),
  )
  const topGroups = computed(() => groups.value.filter((g) => g.basketQty > 0))
  const bottomGroups = computed(() => groups.value.filter((g) => g.basketQty < g.totalQty))

  function lineKey(articleId, note, additions) {
    return `${articleId}:${note || ''}:${store.additionsSignature(additions || [])}`
  }

  function initGroups(data) {
    const arts = event.value?.articles || {}
    const lg = data?.line_groups || []
    groups.value = lg.map((g) => {
      const additions = g.additions || []
      const line = { article_id: g.article_id, additions }
      return {
        key: lineKey(g.article_id, g.note, additions),
        article_id: g.article_id,
        note: g.note || '',
        additions,
        totalQty: g.total_qty,
        unitCents: g.unit_cents,
        basketQty: g.total_qty,
        name: store.articleName(g.article_id),
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
    return topGroups.value.map((g) => ({
      article_id: g.article_id,
      note: g.note,
      qty: g.basketQty,
      additions: (g.additions || []).map((a) => ({
        article_id: a.article_id,
        qty: a.qty ?? 1,
      })),
    }))
  }

  async function paymentsForAmount(cents) {
    if (paymentMode.value === 'instant') {
      return buildPayment(cents, 'instant')
    }
    const payType = await pickPaymentType(event.value, cents)
    return buildPayment(cents, payType)
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
        }),
      })
      if (res.remaining_cents <= 0) {
        onFullySettled?.()
        return res
      }
      store.showToast(`Teilbetrag bezahlt. Rest: ${formatAmount(res.remaining_cents)}`, 'ok')
      await reload()
      return res
    } finally {
      paying.value = false
    }
  }

  async function onGreenCheck(onFullySettled) {
    if (!basketCents.value) return
    const payments = await paymentsForAmount(basketCents.value)
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
    basketCents,
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
