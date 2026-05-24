<template>
  <div class="order-screen">
    <OrderScreenHeader
      :table="register?.name || 'Kasse'"
      :total-label="totalLabel"
      :qty="cartCount"
      :disabled="submitting || !cartCount"
      @back="goBack"
      @submit="submitOrder"
    />

    <div class="order-body">
      <CartPanel
        class="cart-half"
        :lines="lines"
        :articles="articles"
        :currency="currency"
        :label-fn="articleName"
        @tap-name="onTapName"
        @tap-qty="onTapQty"
        @tap-price="onTapPrice"
      />

      <div class="grid-half">
        <EventLayoutGrid
          v-if="layout"
          :layout="layout"
          :event="event"
          @pick="onPickArticles"
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
      :name="qtyModalLine ? articleName(qtyModalLine.article_id) : ''"
      :max="qtyModalMax"
      :model-value="qtyModalLine?.qty || 0"
      @close="qtyModalOpen = false"
      @confirm="onQtyConfirm"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useCart } from '../composables/useCart'
import { useEventContext } from '../composables/useEventContext'
import { formatMoney } from '../utils/money'
import { articlesForIds, getDefaultLayout, hasAdditions, resolveStationUuidForArticle } from '../utils/bundleHelpers'
import { buildPayment } from '../utils/paymentTypes'
import { pickPaymentType } from '../utils/pickPaymentType'
import { useRegisterDisplay } from '../composables/useRegisterDisplay'
import OrderScreenHeader from '../components/OrderScreenHeader.vue'
import CartPanel from '../components/CartPanel.vue'
import EventLayoutGrid from '../components/EventLayoutGrid.vue'
import StationFallbackList from '../components/StationFallbackList.vue'
import ArticlePickerSheet from '../components/ArticlePickerSheet.vue'
import AdditionsPickerSheet from '../components/AdditionsPickerSheet.vue'
import QtyInputModal from '../components/QtyInputModal.vue'

const router = useRouter()
const submitting = ref(false)
const sheetOpen = ref(false)
const sheetArticles = ref([])
const qtyModalOpen = ref(false)
const qtyModalLine = ref(null)
const additionsPickerOpen = ref(false)
const additionsPickerArticle = ref(null)
const pendingAdd = ref(null)

const { register, event, currency, updateDisplay, hubRoute } = useRegisterDisplay()
const {
  lines,
  cartCount,
  cartTotalCents,
  addCartLine,
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
const totalLabel = computed(() => formatMoney(cartTotalCents.value, currency.value))

const qtyModalMax = computed(() => {
  const line = qtyModalLine.value
  if (!line) return 999
  const avail = availableQty(line.article_id, line.lineId)
  if (avail === null) return 999
  return line.qty + avail
})

function orderingPayload(extra = {}) {
  return {
    state: 'ordering',
    show_twint: false,
    twint_qr_data_url: null,
    ...extra,
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
  const avail = availableQty(line.article_id, line.lineId)
  if (avail !== null && qty > line.qty + avail) {
    showToast(`Nur noch ${avail} verfügbar`, 'err')
    qty = line.qty + avail
  }
  if (qty <= 0) removeCartLine(line.lineId)
  else updateCartLine(line.lineId, { qty })
  qtyModalOpen.value = false
}

function onTapPrice(lineId) {
  decrementCartLine(lineId)
}

function goBack() {
  clearCart()
  updateDisplay({ state: 'idle', lines: [], total_cents: 0, show_twint: false, twint_qr_data_url: null })
  router.push(hubRoute())
}

async function submitOrder() {
  if (!cartCount.value || !event.value || !register.value) return
  let payType
  try {
    payType = await pickPaymentType(event.value, cartTotalCents.value, {
      onTwintShow: ({ dataUrl, amountCents }) =>
        updateDisplay({
          state: 'twint',
          show_twint: true,
          twint_qr_data_url: dataUrl,
          total_cents: amountCents,
        }),
      onTwintHide: () => updateDisplay(orderingPayload()),
    })
  } catch {
    return
  }
  submitting.value = true
  try {
    const client_order_id = `pwa-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    const payloadLines = lines.value.map((l) => ({
      article_id: l.article_id,
      qty: l.qty,
      station_uuid: l.station_uuid,
      note: l.note || '',
      additions: (l.additions || []).map((a) => ({ article_id: a.article_id, qty: a.qty ?? 1 })),
    }))
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
        payments: buildPayment(cartTotalCents.value, payType),
      }),
    })
    if (res.articles) patchEventArticles(event.value.id, res.articles)
    clearCart()
    showToast(`Pickup ${res.pickup_code}`, 'ok')
    await updateDisplay({
      state: 'submitted',
      pickup_code: res.pickup_code,
      pickup_status: res.pickup_status,
      lines: [],
      total_cents: 0,
      show_twint: false,
      twint_qr_data_url: null,
    })
    router.push(hubRoute())
  } catch (e) {
    showToast(e.message || 'Fehler', 'err')
  } finally {
    submitting.value = false
  }
}

watch(lines, () => updateDisplay(orderingPayload()), { deep: true })

onMounted(() => {
  if (!register.value) {
    router.replace({ name: 'registers' })
    return
  }
  updateDisplay(orderingPayload({ lines: [], total_cents: 0 }))
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
@media (max-width: 800px) {
  .order-body {
    grid-template-columns: 1fr;
  }
}
</style>
