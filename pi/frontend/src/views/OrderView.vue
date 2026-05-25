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
        :label-fn="cartLineLabel"
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

    <LayoutCellPickerSheet
      :open="cellPickerOpen"
      :items="cellPickerItems"
      @close="cellPickerOpen = false"
      @pick="onCellPickerPick"
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
import { api } from '../api'
import { useCart } from '../composables/useCart'
import { useEventContext } from '../composables/useEventContext'
import { formatMoney } from '../utils/money'
import { getDefaultLayout, articlesForIds, hasAdditions, resolveStationUuidForArticle } from '../utils/bundleHelpers'
import OrderScreenHeader from '../components/OrderScreenHeader.vue'
import CartPanel from '../components/CartPanel.vue'
import EventLayoutGrid from '../components/EventLayoutGrid.vue'
import LayoutCellPickerSheet from '../components/LayoutCellPickerSheet.vue'
import StationFallbackList from '../components/StationFallbackList.vue'
import ArticlePickerSheet from '../components/ArticlePickerSheet.vue'
import AdditionsPickerSheet from '../components/AdditionsPickerSheet.vue'
import QtyInputModal from '../components/QtyInputModal.vue'

const route = useRoute()
const router = useRouter()
const {
  lines,
  cartCount,
  cartTotalCents,
  activeTableNumber,
  addCartLine,
  addVoucherCartLine,
  removeCartLine,
  updateCartLine,
  decrementCartLine,
  availableQty,
  getArticle,
  articleName,
  cartLineLabel,
  clearCart,
} = useCart()
const { event, currency, waiter, showToast, patchEventArticles } = useEventContext()
const submitting = ref(false)
const sheetOpen = ref(false)
const sheetArticles = ref([])
const cellPickerOpen = ref(false)
const cellPickerItems = ref([])
const qtyModalOpen = ref(false)
const qtyModalLine = ref(null)
const additionsPickerOpen = ref(false)
const additionsPickerArticle = ref(null)
const pendingAdd = ref(null)

const tableNumber = computed(() => {
  const q = route.query.table
  const n = parseInt(String(q ?? activeTableNumber.value), 10)
  return Number.isFinite(n) ? n : 0
})

watch(
  tableNumber,
  (n) => {
    if (n >= 1 && n <= 99999) activeTableNumber.value = n
    else if (!route.query.table) router.replace({ name: 'table-new' })
  },
  { immediate: true },
)

const articles = computed(() => event.value?.articles || {})
const layout = computed(() => (event.value ? getDefaultLayout(event.value) : null))
const totalLabel = computed(() => formatMoney(cartTotalCents.value, currency.value))
const paymentMode = computed(() => (event.value?.payment_mode || 'pay_later').toLowerCase())

const qtyModalMax = computed(() => {
  const line = qtyModalLine.value
  if (!line) return 999
  const avail = availableQty(line.article_id, line.lineId)
  if (avail === null) return 999
  return line.qty + avail
})

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
    addOne(item.article_id)
  }
}

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

function goHub() {
  router.push({ name: 'hub' })
}

async function submitOrder() {
  if (!cartCount.value || !tableNumber.value || !event.value) return
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
        additions: (l.additions || []).map((a) => ({
          article_id: a.article_id,
          qty: a.qty ?? 1,
        })),
      }
    })
    const res = await api('/v1/orders', {
      method: 'POST',
      body: JSON.stringify({
        client_order_id,
        event_id: event.value.id,
        table_number: tableNumber.value,
        waiter_uuid: waiter.value?.uuid ?? null,
        lines: payloadLines,
        payments: [],
      }),
    })
    if (res.articles) {
      patchEventArticles(event.value.id, res.articles)
    }
    const pm = res.payment_mode || paymentMode.value
    if (pm === 'pay_now') {
      clearCart()
      router.push({
        name: 'pay-table',
        query: { table: String(tableNumber.value) },
      })
      return
    }
    clearCart()
    activeTableNumber.value = null
    showToast('Bestellung gespeichert.', 'ok')
    router.replace({ name: 'hub' })
  } catch (e) {
    showToast(e.message || 'Fehler', 'err')
  } finally {
    submitting.value = false
  }
}
</script>
