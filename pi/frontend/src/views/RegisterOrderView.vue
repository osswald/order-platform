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
import { useRoute, useRouter } from 'vue-router'
import * as store from '../store'
import { api } from '../api'
import { formatMoney } from '../utils/money'
import { articlesForIds, getDefaultLayout, hasAdditions, resolveStationUuidForArticle } from '../utils/bundleHelpers'
import { buildPayment } from '../utils/paymentTypes'
import { pickPaymentType } from '../utils/pickPaymentType'
import OrderScreenHeader from '../components/OrderScreenHeader.vue'
import CartPanel from '../components/CartPanel.vue'
import EventLayoutGrid from '../components/EventLayoutGrid.vue'
import StationFallbackList from '../components/StationFallbackList.vue'
import ArticlePickerSheet from '../components/ArticlePickerSheet.vue'
import AdditionsPickerSheet from '../components/AdditionsPickerSheet.vue'
import QtyInputModal from '../components/QtyInputModal.vue'

const route = useRoute()
const router = useRouter()
const submitting = ref(false)
const sheetOpen = ref(false)
const sheetArticles = ref([])
const qtyModalOpen = ref(false)
const qtyModalLine = ref(null)
const additionsPickerOpen = ref(false)
const additionsPickerArticle = ref(null)
const pendingAdd = ref(null)

const event = computed(() => store.selectedEvent.value)
const registerUuid = computed(() => String(route.params.registerUuid || ''))
const register = computed(() =>
  (event.value?.configuration?.cash_registers || []).find((reg) => String(reg.uuid) === registerUuid.value) || null,
)
const lines = computed(() => store.cartLines.value)
const cartCount = computed(() => store.cartCount.value)
const articles = computed(() => event.value?.articles || {})
const currency = computed(() => event.value?.currency || 'EUR')
const layout = computed(() => {
  const layouts = event.value?.configuration?.app_layouts || []
  return layouts.find((lo) => String(lo.uuid) === String(register.value?.layout_uuid)) || getDefaultLayout(event.value)
})
const totalLabel = computed(() => formatMoney(store.cartTotalCents.value, currency.value))
const articleName = (id) => store.articleName(id)

const qtyModalMax = computed(() => {
  const line = qtyModalLine.value
  if (!line) return 999
  const avail = store.availableQty(line.article_id, line.lineId)
  if (avail === null) return 999
  return line.qty + avail
})

async function updateDisplay(extra = {}) {
  if (!event.value?.id || !register.value?.uuid) return
  try {
    await api(`/v1/registers/${encodeURIComponent(register.value.uuid)}/display`, {
      method: 'PUT',
      body: JSON.stringify({
        event_id: event.value.id,
        payload: {
          register_name: register.value.name,
          lines: lines.value,
          total_cents: store.cartTotalCents.value,
          currency: currency.value,
          ...extra,
        },
      }),
    })
  } catch {
    /* second screen is best-effort */
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
  const art = store.getArticle(articleId)
  if (art && hasAdditions(art)) {
    pendingAdd.value = { articleId, qty }
    additionsPickerArticle.value = art
    additionsPickerOpen.value = true
    return
  }
  const su = resolveStationUuidForArticle(event.value, articleId)
  store.addCartLine({ article_id: articleId, qty, station_uuid: su, note: '', additions: [] })
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
  store.addCartLine({
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
  store.addCartLine({
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
  const avail = store.availableQty(line.article_id, line.lineId)
  if (avail !== null && qty > line.qty + avail) {
    store.showToast(`Nur noch ${avail} verfügbar`, 'err')
    qty = line.qty + avail
  }
  if (qty <= 0) store.removeCartLine(line.lineId)
  else store.updateCartLine(line.lineId, { qty })
  qtyModalOpen.value = false
}

function onTapPrice(lineId) {
  store.decrementCartLine(lineId)
}

function goBack() {
  store.clearCart()
  updateDisplay({ state: 'idle', lines: [], total_cents: 0 })
  router.push({ name: 'registers' })
}

async function submitOrder() {
  if (!cartCount.value || !event.value || !register.value) return
  let payType
  try {
    payType = await pickPaymentType(event.value, store.cartTotalCents.value)
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
        waiter_uuid: store.waiter.value?.uuid ?? null,
        order_source: 'cash_register',
        cash_register_uuid: register.value.uuid,
        lines: payloadLines,
        payments: buildPayment(store.cartTotalCents.value, payType),
      }),
    })
    if (res.articles) store.patchEventArticles(event.value.id, res.articles)
    store.clearCart()
    store.showToast(`Pickup ${res.pickup_code}`, 'ok')
    await updateDisplay({
      state: 'submitted',
      pickup_code: res.pickup_code,
      pickup_status: res.pickup_status,
      lines: [],
      total_cents: 0,
    })
  } catch (e) {
    store.showToast(e.message || 'Fehler', 'err')
  } finally {
    submitting.value = false
  }
}

watch(lines, () => updateDisplay({ state: cartCount.value ? 'ordering' : 'idle' }), { deep: true })
watch(register, () => updateDisplay({ state: 'idle' }), { immediate: true })

onMounted(() => {
  if (!register.value) router.replace({ name: 'registers' })
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
