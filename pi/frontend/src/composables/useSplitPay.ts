import { ref, computed, type Ref } from 'vue'
import { additionsSignature, articleName, showToast } from '@/store'
import { api } from '@/api'
import type { DiscountIn, EdgeBundleEvent, LineAdditionIn, PaymentIn } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import { formatMoney } from '@/utils/money'
import { lineAdditionLabels } from '@/utils/bundleHelpers'
import { buildPayment } from '@/utils/paymentTypes'
import { resolvePaymentsForAmount } from '@/utils/resolvePayment'
import {
  basketCentsAfterVoucher,
  sumGroupBasketCents,
  sumVoucherCreditCents,
  type VoucherRedemption,
} from '@/utils/splitPay'

export interface SplitPaySummary {
  total_cents?: number
  line_groups?: Array<{
    article_id: number
    note?: string
    additions?: LineAdditionIn[]
    discount?: DiscountIn | null
    total_qty: number
    unit_cents?: number
    line_total_cents?: number
  }>
  remaining_cents?: number
}

export interface SplitPayGroupRow {
  key: string
  article_id: number
  note: string
  additions: LineAdditionIn[]
  discount: DiscountIn | null
  totalQty: number
  unitCents?: number
  lineTotalCents: number
  basketQty: number
  name: string
  additionLabels: Array<{ id: number; name: string }>
}

export interface VoucherRedemptionSelection extends VoucherRedemption {
  voucher_definition_uuid: string
  article_id: number
  note?: string
  qty?: number
  additions?: LineAdditionIn[]
}

export interface UseSplitPayOptions {
  event: Ref<EdgeBundleEvent | null>
  paymentMode: Ref<string>
  loadSummary: () => Promise<SplitPaySummary>
  settlePartialPath: () => string
  voucherRedemptions?: Ref<VoucherRedemptionSelection[]>
}

export function useSplitPay({
  event,
  paymentMode,
  loadSummary,
  settlePartialPath,
  voucherRedemptions = ref([]),
}: UseSplitPayOptions) {
  const summary = ref<SplitPaySummary | null>(null)
  const groups = ref<SplitPayGroupRow[]>([])
  const loading = ref(true)
  const paying = ref(false)
  const qtyModalOpen = ref(false)
  const qtyModalGroup = ref<SplitPayGroupRow | null>(null)

  const totalCents = computed(() => summary.value?.total_cents || 0)

  const rawBasketCents = computed(() => sumGroupBasketCents(groups.value))
  const voucherCreditCents = computed(() =>
    sumVoucherCreditCents(voucherRedemptions.value),
  )
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

  function lineKey(
    articleId: number,
    note: string | undefined,
    additions: LineAdditionIn[] | undefined,
  ): string {
    return `${articleId}:${note || ''}:${additionsSignature(additions || [])}`
  }

  function initGroups(data: SplitPaySummary | null): void {
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

  function moveAllToBottom(): void {
    for (const g of groups.value) g.basketQty = 0
  }

  function moveAllToTop(): void {
    for (const g of groups.value) g.basketQty = g.totalQty
  }

  function bumpBasket(g: SplitPayGroupRow, delta: number): void {
    g.basketQty = Math.min(g.totalQty, Math.max(0, g.basketQty + delta))
  }

  function openQtyModal(g: SplitPayGroupRow): void {
    qtyModalGroup.value = g
    qtyModalOpen.value = true
  }

  function onQtyConfirm(n: number | string): void {
    if (qtyModalGroup.value) {
      const g = qtyModalGroup.value
      g.basketQty = Math.min(g.totalQty, Math.max(0, Number(n) || 0))
    }
    qtyModalOpen.value = false
  }

  function selectionsPayload() {
    return topGroups.value.map((g) => {
      const row: {
        article_id: number
        note: string
        qty: number
        additions: Array<{ article_id: number; qty: number }>
        discount?: DiscountIn
      } = {
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

  async function paymentsForAmount(cents: number): Promise<PaymentIn[]> {
    if (paymentMode.value === 'instant') {
      return buildPayment(cents, 'instant')
    }
    if (!event.value) throw new Error('Kein Event')
    return resolvePaymentsForAmount(event.value, cents)
  }

  async function reload(): Promise<SplitPaySummary> {
    const data = await loadSummary()
    summary.value = data
    initGroups(data)
    return data
  }

  async function settlePartial(
    payments: PaymentIn[],
    onFullySettled?: () => void,
  ): Promise<SplitPaySummary> {
    paying.value = true
    try {
      if (!event.value) throw new Error('Kein Event')
      const res = await api<SplitPaySummary>(settlePartialPath(), {
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
      if ((res.remaining_cents ?? 0) <= 0) {
        onFullySettled?.()
        return res
      }
      showToast(`Teilbetrag bezahlt. Rest: ${formatMoney(res.remaining_cents, event.value?.currency || 'CHF')}`, 'ok')
      await reload()
      return res
    } finally {
      paying.value = false
    }
  }

  async function onGreenCheck(onFullySettled?: () => void): Promise<SplitPaySummary | undefined> {
    if (!rawBasketCents.value) return
    let payments: PaymentIn[]
    try {
      payments = await paymentsForAmount(basketCents.value)
    } catch (e: unknown) {
      const message = getErrorMessage(e, 'Zahlung abgebrochen.')
      if (message !== 'cancelled') {
        showToast(message, 'err')
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
