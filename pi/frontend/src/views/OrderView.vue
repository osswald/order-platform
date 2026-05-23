<template>
  <div class="order-screen">
    <OrderScreenHeader
      :table="tableNumber"
      :total-label="totalLabel"
      :qty="cartCount"
      :disabled="submitting || !cartCount"
      @back="goHub"
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
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as store from '../store'
import { api } from '../api'
import { formatMoney } from '../utils/money'
import { getDefaultLayout, articlesForIds, hasAdditions, resolveStationUuidForArticle } from '../utils/bundleHelpers'
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

const tableNumber = computed(() => {
  const q = route.query.table
  const n = parseInt(String(q ?? store.activeTableNumber.value), 10)
  return Number.isFinite(n) ? n : 0
})

watch(
  tableNumber,
  (n) => {
    if (n >= 1 && n <= 99999) store.activeTableNumber.value = n
    else if (!route.query.table) router.replace({ name: 'table-new' })
  },
  { immediate: true },
)

const event = computed(() => store.selectedEvent.value)
const lines = computed(() => store.cartLines.value)
const cartCount = computed(() => store.cartCount.value)
const articles = computed(() => event.value?.articles || {})
const currency = computed(() => event.value?.currency || 'EUR')
const layout = computed(() => (event.value ? getDefaultLayout(event.value) : null))
const totalLabel = computed(() => formatMoney(store.cartTotalCents.value, currency.value))
const paymentMode = computed(() => (event.value?.payment_mode || 'pay_later').toLowerCase())
const articleName = (id) => store.articleName(id)

const qtyModalMax = computed(() => {
  const line = qtyModalLine.value
  if (!line) return 999
  const avail = store.availableQty(line.article_id, line.lineId)
  if (avail === null) return 999
  return line.qty + avail
})

function onPickArticles(articleIds) {
  const arts = articlesForIds(event.value, articleIds)
  if (!arts.length) return
  if (arts.length === 1) {
    addOne(arts[0].id)
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

function addOne(articleId) {
  beginAdd(articleId, 1)
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

function goHub() {
  router.push({ name: 'hub' })
}

async function submitOrder() {
  if (!cartCount.value || !tableNumber.value || !event.value) return
  submitting.value = true
  try {
    const client_order_id = `pwa-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    const payloadLines = lines.value.map((l) => ({
      article_id: l.article_id,
      qty: l.qty,
      station_uuid: l.station_uuid,
      note: l.note || '',
      additions: (l.additions || []).map((a) => ({
        article_id: a.article_id,
        qty: a.qty ?? 1,
      })),
    }))
    const totalCents = store.cartTotalCents.value
    const res = await api('/v1/orders', {
      method: 'POST',
      body: JSON.stringify({
        client_order_id,
        event_id: event.value.id,
        table_number: tableNumber.value,
        waiter_uuid: store.waiter.value?.uuid ?? null,
        lines: payloadLines,
        payments: [],
      }),
    })
    if (res.articles) {
      store.patchEventArticles(event.value.id, res.articles)
    }
    const pm = res.payment_mode || paymentMode.value
    if (pm === 'pay_now') {
      store.clearCart()
      router.push({
        name: 'pay-order',
        params: { id: String(res.local_order_id) },
        query: { table: String(tableNumber.value), total_cents: String(totalCents) },
      })
      return
    }
    store.clearCart()
    store.activeTableNumber.value = null
    store.showToast('Bestellung gespeichert.', 'ok')
    router.replace({ name: 'hub' })
  } catch (e) {
    store.showToast(e.message || 'Fehler', 'err')
  } finally {
    submitting.value = false
  }
}
</script>
