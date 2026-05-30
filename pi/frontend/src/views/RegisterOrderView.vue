<template>
  <div class="order-screen">
    <OrderScreenHeader
      :table="register?.name || 'Kasse'"
      :total-label="totalLabel"
      :qty="cartCount"
      :show-menu="canRedeemVoucher"
      :disabled="submitting || !cartCount"
      @back="goBack"
      @menu="openVoucherRedeem"
      @submit="submitOrder"
    />

    <div class="order-body">
      <div class="cart-half">
        <ul v-if="voucherBasketLines.length" class="line-list register-voucher-list">
          <SplitPayVoucherRow
            v-for="(v, vi) in voucherBasketLines"
            :key="v.key"
            :label="v.label"
            :amount-cents="v.appliedCents"
            @remove="removeVoucherLine(vi)"
          />
        </ul>
        <CartPanel
          :lines="lines"
          :articles="articles"
          :event="event"
          :currency="currency"
          :label-fn="cartLineLabel"
          @tap-name="onTapName"
          @tap-qty="onTapQty"
          @tap-price="onTapPrice"
        />
      </div>

      <div class="grid-half">
        <EventLayoutGrid
          v-if="layout"
          :layout="layout"
          :event="event"
          @pick="onPickArticles"
          @pick-voucher="onPickVoucher"
          @pick-cell="onPickCell"
        />
        <StationFallbackList v-else-if="event" :event="event" @pick="onPickArticles" />
      </div>
    </div>

    <ArticlePickerSheet
      :open="sheetOpen"
      :articles="sheetArticles"
      :event-currency="currency"
      @close="sheetOpen = false"
      @add="onAddFromSheet"
    />

    <AdditionsPickerSheet
      :open="additionsPickerOpen"
      :article-name="additionsPickerArticle?.name || ''"
      :additions="additionsPickerArticle?.additions || []"
      :currency="currency"
      @cancel="onAdditionsCancel"
      @confirm="onAdditionsConfirm"
    />

    <QtyInputModal
      :open="qtyModalOpen"
      :name="qtyModalLine ? cartLineLabel(qtyModalLine) : ''"
      :max="qtyModalMax"
      :model-value="qtyModalLine?.qty || 0"
      @close="qtyModalOpen = false"
      @confirm="onQtyConfirm"
    />

    <LayoutCellPickerSheet
      :open="cellPickerOpen"
      :items="cellPickerItems"
      @close="cellPickerOpen = false"
      @pick="onCellPickerPick"
    />

    <VoucherRedeemSheet
      :open="voucherSheetOpen"
      :event="event"
      :gross-cents="registerArticleCents"
      :selections="registerSelections"
      :line-groups="registerLineGroups"
      @close="voucherSheetOpen = false"
      @apply="onVoucherApply"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useCart } from '../composables/useCart'
import { useEventContext } from '../composables/useEventContext'
import { formatMoney, lineTotalCents, lineUnitCents } from '../utils/money'
import {
  articlesForIds,
  getDefaultLayout,
  hasAdditions,
  resolveStationUuidForArticle,
  voucherDefinitionByUuid,
  cartLineLabelForEvent,
} from '../utils/bundleHelpers'
import { buildPayment } from '../utils/paymentTypes'
import { pickPaymentType } from '../utils/pickPaymentType'
import { useRoute } from 'vue-router'
import { useRegisterDisplay } from '../composables/useRegisterDisplay'
import OrderScreenHeader from '../components/OrderScreenHeader.vue'
import CartPanel from '../components/CartPanel.vue'
import EventLayoutGrid from '../components/EventLayoutGrid.vue'
import LayoutCellPickerSheet from '../components/LayoutCellPickerSheet.vue'
import StationFallbackList from '../components/StationFallbackList.vue'
import ArticlePickerSheet from '../components/ArticlePickerSheet.vue'
import AdditionsPickerSheet from '../components/AdditionsPickerSheet.vue'
import QtyInputModal from '../components/QtyInputModal.vue'
import VoucherRedeemSheet from '../components/VoucherRedeemSheet.vue'
import SplitPayVoucherRow from '../components/SplitPayVoucherRow.vue'

const router = useRouter()
const route = useRoute()
const submitting = ref(false)
const voucherSheetOpen = ref(false)
const voucherRedemptions = ref([])
const cellPickerOpen = ref(false)
const cellPickerItems = ref([])
const sheetOpen = ref(false)
const sheetArticles = ref([])
const qtyModalOpen = ref(false)
const qtyModalLine = ref(null)
const additionsPickerOpen = ref(false)
const additionsPickerArticle = ref(null)
const pendingAdd = ref(null)

const {
  register,
  event,
  currency,
  updateDisplay,
  pushDisplayPayload,
  setDisplayIdle,
  scheduleIdleAfterPickup,
  clearPickupHold,
  hubRoute,
} = useRegisterDisplay()
const {
  lines,
  cartCount,
  cartTotalCents,
  addCartLine,
  addVoucherCartLine,
  cartLineLabel,
  removeCartLine,
  updateCartLine,
  decrementCartLine,
  availableQty,
  getArticle,
  articleName,
  clearCart,
} = useCart()
const { waiter, showToast, patchEventArticles } = useEventContext()

const articles = computed(() => event.value?.articles || {})
const layout = computed(() => {
  const layouts = event.value?.configuration?.app_layouts || []
  return layouts.find((lo) => String(lo.uuid) === String(register.value?.layout_uuid)) || getDefaultLayout(event.value)
})
const registerArticleCents = computed(() =>
  lines.value
    .filter((l) => l.kind !== 'voucher_sale')
    .reduce((s, l) => s + lineTotalCents(l, articles.value, event.value), 0),
)
const voucherCreditCents = computed(() =>
  voucherRedemptions.value.reduce((s, r) => s + Math.max(0, Number(r.applied_cents) || 0), 0),
)
const registerPayableCents = computed(() =>
  Math.max(0, cartTotalCents.value - voucherCreditCents.value),
)
const canRedeemVoucher = computed(() => lines.value.some((l) => l.kind !== 'voucher_sale'))
const totalLabel = computed(() => {
  const base = formatMoney(registerPayableCents.value, currency.value)
  if (!voucherCreditCents.value) return base
  return `${base} (−${formatMoney(voucherCreditCents.value, currency.value)} Gutschein)`
})
const registerSelections = computed(() =>
  lines.value
    .filter((l) => l.kind !== 'voucher_sale')
    .map((l) => ({
      article_id: l.article_id,
      note: l.note || '',
      qty: l.qty,
      additions: (l.additions || []).map((a) => ({
        article_id: a.article_id,
        qty: a.qty ?? 1,
      })),
    })),
)
const registerLineGroups = computed(() =>
  lines.value
    .filter((l) => l.kind !== 'voucher_sale')
    .map((l) => ({
      article_id: l.article_id,
      note: l.note || '',
      additions: l.additions || [],
      unit_cents: lineUnitCents(l, articles.value, event.value),
    })),
)
const voucherBasketLines = computed(() =>
  voucherRedemptions.value.map((r, index) => {
    const vd = voucherDefinitionByUuid(event.value, r.voucher_definition_uuid)
    const name = vd?.name || 'Gutschein'
    return {
      key: `voucher-${index}-${r.voucher_definition_uuid}`,
      label: `${name}`,
      appliedCents: Math.max(0, Number(r.applied_cents) || 0),
    }
  }),
)

const qtyModalMax = computed(() => {
  const line = qtyModalLine.value
  if (!line) return 999
  if (line.kind === 'voucher_sale') return 99
  const avail = availableQty(line.article_id, line.lineId)
  if (avail === null) return 999
  return line.qty + avail
})

function orderingPayload(extra = {}) {
  return {
    state: 'ordering',
    show_twint: false,
    twint_qr_data_url: null,
    total_cents: registerPayableCents.value,
    voucher_lines: voucherBasketLines.value.map((v) => ({
      key: v.key,
      label: v.label,
      applied_cents: v.appliedCents,
    })),
    lines: lines.value.map((l) => ({
      ...l,
      display_label: cartLineLabelForEvent(l, event.value),
    })),
    ...extra,
  }
}

function onPickVoucher(vd) {
  addVoucherCartLine({ voucher_definition_uuid: vd.uuid, qty: 1 })
}

function onPickCell({ items }) {
  cellPickerItems.value = items || []
  cellPickerOpen.value = true
}

function onCellPickerPick(item) {
  cellPickerOpen.value = false
  if (!item) return
  if (item.type === 'voucher' && item.voucher) {
    onPickVoucher(item.voucher)
    return
  }
  if (item.type === 'article' && item.article_id != null) {
    beginAdd(item.article_id, 1)
  }
}

function onPickArticles(articleIds) {
  const arts = articlesForIds(event.value, articleIds)
  if (!arts.length) return
  if (arts.length === 1) {
    beginAdd(arts[0].id, 1)
    return
  }
  sheetArticles.value = arts
  sheetOpen.value = true
}

function beginAdd(articleId, qty = 1) {
  const art = getArticle(articleId)
  if (art && hasAdditions(art)) {
    pendingAdd.value = { articleId, qty }
    additionsPickerArticle.value = art
    additionsPickerOpen.value = true
    return
  }
  const su = resolveStationUuidForArticle(event.value, articleId)
  addCartLine({ article_id: articleId, qty, station_uuid: su, note: '', additions: [] })
}

function onAddFromSheet({ article_id, qty }) {
  beginAdd(article_id, qty)
  sheetOpen.value = false
}

function onAdditionsCancel() {
  additionsPickerOpen.value = false
  pendingAdd.value = null
  additionsPickerArticle.value = null
}

function onAdditionsConfirm(additions) {
  const p = pendingAdd.value
  if (!p) return
  const su = resolveStationUuidForArticle(event.value, p.articleId)
  addCartLine({
    article_id: p.articleId,
    qty: p.qty,
    station_uuid: su,
    note: '',
    additions,
  })
  onAdditionsCancel()
}

function onTapName(line) {
  if (line.kind === 'voucher_sale') {
    addVoucherCartLine({
      voucher_definition_uuid: line.voucher_definition_uuid,
      qty: 1,
      unit_cents: line.unit_cents,
    })
    return
  }
  const su = resolveStationUuidForArticle(event.value, line.article_id)
  addCartLine({
    article_id: line.article_id,
    qty: 1,
    station_uuid: line.station_uuid ?? su,
    note: line.note || '',
    additions: line.additions || [],
    excludeLineId: line.lineId,
  })
}

function onTapQty(line) {
  qtyModalLine.value = line
  qtyModalOpen.value = true
}

function onQtyConfirm(n) {
  const line = qtyModalLine.value
  if (!line) return
  let qty = Math.max(0, Math.min(qtyModalMax.value, Number(n) || 0))
  if (line.kind !== 'voucher_sale') {
    const avail = availableQty(line.article_id, line.lineId)
    if (avail !== null && qty > line.qty + avail) {
      showToast(`Nur noch ${avail} verfügbar`, 'err')
      qty = line.qty + avail
    }
  }
  if (qty <= 0) removeCartLine(line.lineId)
  else updateCartLine(line.lineId, { qty })
  qtyModalOpen.value = false
}

function onTapPrice(lineId) {
  decrementCartLine(lineId)
}

function syncDisplayToCart() {
  if (submitting.value || route.name !== 'register-order') return
  updateDisplay(orderingPayload())
}

function goBack() {
  clearPickupHold()
  clearCart()
  setDisplayIdle()
  router.push(hubRoute())
}

function openVoucherRedeem() {
  if (!registerArticleCents.value) {
    showToast('Keine Artikel-Positionen für Gutschein', 'err')
    return
  }
  voucherSheetOpen.value = true
}

function onVoucherApply(redemption) {
  voucherRedemptions.value = [...voucherRedemptions.value, redemption]
  voucherSheetOpen.value = false
  showToast('Gutschein berücksichtigt', 'ok')
}

function removeVoucherLine(index) {
  voucherRedemptions.value = voucherRedemptions.value.filter((_, i) => i !== index)
}

async function submitOrder() {
  if (!cartCount.value || !event.value || !register.value) return
  let payType
  try {
    payType = await pickPaymentType(event.value, registerPayableCents.value, {
      onTwintShow: ({ dataUrl, amountCents }) =>
        updateDisplay({
          state: 'twint',
          show_twint: true,
          twint_qr_data_url: dataUrl,
          total_cents: amountCents,
        }),
      onTwintHide: () => {},
    })
  } catch {
    return
  }
  submitting.value = true
  try {
    const client_order_id = `pwa-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    const payloadLines = lines.value.map((l) => {
      if (l.kind === 'voucher_sale') {
        return {
          kind: 'voucher_sale',
          voucher_definition_uuid: l.voucher_definition_uuid,
          qty: l.qty,
          unit_cents: l.unit_cents,
        }
      }
      return {
        article_id: l.article_id,
        qty: l.qty,
        station_uuid: l.station_uuid,
        note: l.note || '',
        additions: (l.additions || []).map((a) => ({ article_id: a.article_id, qty: a.qty ?? 1 })),
      }
    })
    const res = await api('/v1/orders', {
      method: 'POST',
      body: JSON.stringify({
        client_order_id,
        event_id: event.value.id,
        table_number: null,
        waiter_uuid: waiter.value?.uuid ?? null,
        order_source: 'cash_register',
        cash_register_uuid: register.value.uuid,
        lines: payloadLines,
        payments: buildPayment(registerPayableCents.value, payType),
        voucher_redemptions: voucherRedemptions.value.map((r) => ({
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
    if (res.articles) patchEventArticles(event.value.id, res.articles)
    scheduleIdleAfterPickup(10000)
    await pushDisplayPayload({
      state: 'submitted',
      pickup_code: res.pickup_code,
      pickup_status: res.pickup_status,
      lines: [],
      total_cents: 0,
      show_twint: false,
      twint_qr_data_url: null,
      voucher_lines: [],
    })
    voucherRedemptions.value = []
    clearCart()
    showToast(`Pickup ${res.pickup_code}`, 'ok')
    await router.push(hubRoute())
  } catch (e) {
    showToast(e.message || 'Fehler', 'err')
  } finally {
    submitting.value = false
  }
}

watch([lines, voucherRedemptions, cartCount], () => syncDisplayToCart(), { deep: true })

onMounted(() => {
  if (!register.value) {
    router.replace({ name: 'registers' })
    return
  }
  clearPickupHold()
  syncDisplayToCart()
})
</script>

<style scoped>
.order-screen {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.order-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(280px, 42%) minmax(0, 1fr);
  gap: 0.75rem;
  padding: 0.75rem;
}
.cart-half,
.grid-half {
  min-height: 0;
}
.cart-half {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 0;
}
.register-voucher-list {
  list-style: none;
  padding: 0;
  margin: 0;
  flex-shrink: 0;
}
@media (max-width: 800px) {
  .order-body {
    grid-template-columns: 1fr;
  }
}
</style>
