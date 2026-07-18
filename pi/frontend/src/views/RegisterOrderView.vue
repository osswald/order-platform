<template>
  <div class="order-screen">
    <OrderScreenHeader
      :table="String(register?.name || 'Kasse')"
      :total-label="totalLabel"
      :qty="cartCount"
      :show-menu="showHeaderMenu"
      :disabled="submitting || !cartCount"
      @back="goBack"
      @menu="orderMenuOpen = true"
      @submit="submitOrder"
    />

    <div class="order-body">
      <div class="cart-half">
        <CartPanel
          :lines="lines"
          :articles="articles"
          :event="event"
          :currency="currency"
          :label-fn="cartLineLabel"
          :discounts-enabled="discountsEnabled"
          :position-comments-enabled="positionCommentsEnabled"
          :order-discount="orderDiscount"
          @tap-name="onTapName"
          @tap-qty="onTapQty"
          @tap-price="onTapPrice"
          @tap-discount="onTapDiscount"
          @tap-comment="onTapComment"
          @remove-order-discount="setOrderDiscount(null)"
        />
      </div>

      <div class="grid-half">
        <EventLayoutGrid
          v-if="layout"
          :layout="layout"
          :event="layoutEvent"
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

    <OrderMenuSheet
      :open="orderMenuOpen"
      :show-order-discount="discountsEnabled"
      :show-voucher="false"
      @close="orderMenuOpen = false"
      @order-discount="openOrderDiscount"
    />

    <LinePositionSheet
      v-if="positionCommentsEnabled"
      :open="linePositionOpen"
      :line="linePositionLine"
      :articles="articles"
      :event="event"
      :currency="currency"
      :position-comments-enabled="positionCommentsEnabled"
      :discounts-enabled="discountsEnabled"
      :presets="positionCommentPresets"
      :initial-tab="linePositionTab"
      @close="linePositionOpen = false"
      @save="onLinePositionSave"
    />

    <LineDiscountSheet
      v-if="!positionCommentsEnabled"
      :open="lineDiscountOpen"
      :line="lineDiscountLine"
      :articles="articles"
      :event="event"
      :currency="currency"
      @close="lineDiscountOpen = false"
      @discount-save="onLineDiscountSave"
    />

    <OrderDiscountSheet
      :open="orderDiscountOpen"
      :lines="lines"
      :articles="articles"
      :event="event"
      :currency="currency"
      :order-discount="orderDiscount"
      @close="orderDiscountOpen = false"
      @discount-save="onOrderDiscountSave"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useCart } from '@/composables/useCart'
import { useEventContext } from '@/composables/useEventContext'
import { discountsEnabled as eventDiscountsEnabled, formatMoney } from '@/utils/money'
import {
  articlesForIds,
  getDefaultLayout,
  hasAdditions,
  positionCommentPresets as bundlePositionCommentPresets,
  positionCommentsEnabled as bundlePositionCommentsEnabled,
  resolveStationUuidForArticle,
  cartLineLabelForEvent,
} from '@/utils/bundleHelpers'
import {
  buildOrderPayloadLines,
  newClientOrderId,
  stockLinesFromPayloadLines,
} from '@/utils/orderSubmit'
import { useRoute } from 'vue-router'
import { useRegisterDisplay } from '@/composables/useRegisterDisplay'
import OrderScreenHeader from '@/components/OrderScreenHeader.vue'
import CartPanel from '@/components/CartPanel.vue'
import EventLayoutGrid from '@/components/EventLayoutGrid.vue'
import LayoutCellPickerSheet from '@/components/LayoutCellPickerSheet.vue'
import StationFallbackList from '@/components/StationFallbackList.vue'
import ArticlePickerSheet from '@/components/ArticlePickerSheet.vue'
import AdditionsPickerSheet from '@/components/AdditionsPickerSheet.vue'
import QtyInputModal from '@/components/QtyInputModal.vue'
import OrderMenuSheet from '@/components/OrderMenuSheet.vue'
import LineDiscountSheet from '@/components/LineDiscountSheet.vue'
import LinePositionSheet from '@/components/LinePositionSheet.vue'
import OrderDiscountSheet from '@/components/OrderDiscountSheet.vue'
import { bundle } from '@/store'
import type {
  EdgeBundleArticle,
  EdgeBundleEvent,
  LocalOrderCreate,
  LocalOrderCreatedResponse,
  OrderLineIn,
  RegisterDisplayPayload,
} from '@/types/api'
import { getErrorMessage, isApiError } from '@/types/api'
import { stockInsufficientMessage } from '@/utils/stockError'
import { validateCartStockBeforeSubmit } from '@/utils/validateCartStock'
import type { CartLine } from '@/types/cart'
import type { SheetOptionItem } from '@/components/SheetOptionList.vue'

interface VoucherDefinition {
  uuid: string
  name?: string
}

const router = useRouter()
const route = useRoute()
const submitting = ref(false)
const cellPickerOpen = ref(false)
const cellPickerItems = ref<SheetOptionItem[]>([])
const sheetOpen = ref(false)
const sheetArticles = ref<EdgeBundleArticle[]>([])
const qtyModalOpen = ref(false)
const qtyModalLine = ref<CartLine | null>(null)
const additionsPickerOpen = ref(false)
const additionsPickerArticle = ref<EdgeBundleArticle | null>(null)
const pendingAdd = ref<{ articleId: number; qty: number } | null>(null)
const orderMenuOpen = ref(false)
const lineDiscountOpen = ref(false)
const lineDiscountLine = ref<CartLine | null>(null)
const linePositionOpen = ref(false)
const linePositionLine = ref<CartLine | null>(null)
const linePositionTab = ref('comment')
const orderDiscountOpen = ref(false)
const layoutEvent = computed((): EdgeBundleEvent => event.value as EdgeBundleEvent)

const discountsEnabled = computed(() => eventDiscountsEnabled(event.value))
const positionCommentsEnabled = computed(() => bundlePositionCommentsEnabled(bundle.value))
const positionCommentPresets = computed(() => bundlePositionCommentPresets(bundle.value))
const showHeaderMenu = computed(() => cartCount.value > 0 && discountsEnabled.value)

const {
  register,
  event,
  currency,
  updateDisplay,
  setDisplayIdle,
  clearPickupHold,
  hubRoute,
} = useRegisterDisplay()
const {
  lines,
  cartCount,
  cartTotalCents,
  orderDiscount,
  setOrderDiscount,
  addCartLine,
  addVoucherCartLine,
  cartLineLabel,
  removeCartLine,
  updateCartLine,
  decrementCartLine,
  availableQty,
  lineQtyModalMax,
  getArticle,
  clearCart,
} = useCart()
const { waiter, showToast, patchEventStock, refreshBundle } = useEventContext()

const articles = computed(() => event.value?.articles || {})
const layout = computed(() => {
  const layouts = event.value?.configuration?.app_layouts || []
  return layouts.find((lo) => String(lo.uuid) === String(register.value?.layout_uuid)) || getDefaultLayout(event.value)
})
const totalLabel = computed(() => formatMoney(cartTotalCents.value, currency.value))

const qtyModalMax = computed(() => {
  const line = qtyModalLine.value
  if (!line) return 999
  if (line.kind === 'voucher_sale') return 99
  const articleId = line.article_id
  if (articleId == null) return 999
  const avail = availableQty(articleId, line.lineId)
  return lineQtyModalMax(avail)
})

function orderingPayload(extra: Partial<RegisterDisplayPayload> = {}): RegisterDisplayPayload {
  return {
    state: 'ordering',
    show_twint: false,
    twint_qr_data_url: null,
    total_cents: cartTotalCents.value,
    voucher_lines: [],
    lines: lines.value.map((l) => ({
      ...l,
      display_label: cartLineLabelForEvent(l, event.value),
    })),
    ...extra,
  } as RegisterDisplayPayload
}

function onPickVoucher(vd: VoucherDefinition) {
  addVoucherCartLine({ voucher_definition_uuid: vd.uuid, qty: 1 })
}

function onPickCell(_payload: { cell: unknown; items: unknown[] }) {
  cellPickerItems.value = (_payload.items || []) as SheetOptionItem[]
  cellPickerOpen.value = true
}

function onCellPickerPick(item: SheetOptionItem) {
  cellPickerOpen.value = false
  if (!item) return
  if (item.type === 'voucher' && item.voucher) {
    onPickVoucher(item.voucher as VoucherDefinition)
    return
  }
  if (item.type === 'article' && item.article_id != null) {
    beginAdd(Number(item.article_id), 1)
  }
}

function onPickArticles(articleIds: number[]) {
  const arts = articlesForIds(event.value, articleIds)
  if (!arts.length) return
  if (arts.length === 1) {
    beginAdd(arts[0].id, 1)
    return
  }
  sheetArticles.value = arts
  sheetOpen.value = true
}

function beginAdd(articleId: number, qty = 1) {
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

function onAddFromSheet({ article_id, qty }: { article_id: number; qty: number }) {
  beginAdd(article_id, qty)
  sheetOpen.value = false
}

function onAdditionsCancel() {
  additionsPickerOpen.value = false
  pendingAdd.value = null
  additionsPickerArticle.value = null
}

function onAdditionsConfirm(additions: OrderLineIn['additions']) {
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

function onTapName(line: CartLine) {
  if (line.kind === 'voucher_sale') {
    if (!line.voucher_definition_uuid) return
    addVoucherCartLine({
      voucher_definition_uuid: line.voucher_definition_uuid,
      qty: 1,
      unit_cents: line.unit_cents,
    })
    return
  }
  const articleId = line.article_id
  if (articleId == null) return
  const su = resolveStationUuidForArticle(event.value, articleId)
  addCartLine({
    article_id: articleId,
    qty: 1,
    station_uuid: line.station_uuid ?? su,
    note: line.note || '',
    additions: line.additions || [],
    excludeLineId: line.lineId,
  })
}

function onTapQty(line: CartLine) {
  qtyModalLine.value = line
  qtyModalOpen.value = true
}

function onQtyConfirm(n: number) {
  const line = qtyModalLine.value
  if (!line) return
  let qty = Math.max(0, Math.min(qtyModalMax.value, Number(n) || 0))
  if (line.kind !== 'voucher_sale') {
    const articleId = line.article_id
    if (articleId == null) return
    const avail = availableQty(articleId, line.lineId)
    if (avail !== null && qty > avail) {
      showToast(`Nur noch ${avail} verfügbar`, 'err')
      qty = avail
    }
  }
  if (qty <= 0) removeCartLine(line.lineId)
  else updateCartLine(line.lineId, { qty })
  qtyModalOpen.value = false
}

function onTapPrice(lineId: string) {
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

function onTapComment(line: CartLine) {
  linePositionLine.value = line
  linePositionTab.value = 'comment'
  linePositionOpen.value = true
}

function onTapDiscount(line: CartLine) {
  if (positionCommentsEnabled.value) {
    linePositionLine.value = line
    linePositionTab.value = 'discount'
    linePositionOpen.value = true
    return
  }
  lineDiscountLine.value = line
  lineDiscountOpen.value = true
}

function onLinePositionSave({
  lineId,
  note,
  discount,
}: {
  lineId: string
  note?: string
  discount?: CartLine['discount']
}) {
  linePositionOpen.value = false
  linePositionLine.value = null
  if (!lineId) return
  const patch: Partial<Pick<CartLine, 'note' | 'discount'>> = {}
  if (note !== undefined) patch.note = note || ''
  if (discount !== undefined) {
    patch.discount = discount || undefined
  }
  updateCartLine(lineId, patch)
}

function onLineDiscountSave({
  lineId,
  discount,
}: {
  lineId: string
  discount?: CartLine['discount']
}) {
  lineDiscountOpen.value = false
  lineDiscountLine.value = null
  if (!lineId) return
  if (discount) {
    updateCartLine(lineId, { discount })
  } else {
    updateCartLine(lineId, { discount: undefined })
  }
}

function openOrderDiscount() {
  orderMenuOpen.value = false
  orderDiscountOpen.value = true
}

function onOrderDiscountSave({ discount }: { discount?: CartLine['discount'] }) {
  orderDiscountOpen.value = false
  setOrderDiscount(discount)
}

async function submitOrder() {
  if (!cartCount.value || !event.value || !register.value) return

  const payloadLines = buildOrderPayloadLines(lines.value, {
    positionCommentsEnabled: positionCommentsEnabled.value,
    discountsEnabled: discountsEnabled.value,
  })
  const stockLines = stockLinesFromPayloadLines(payloadLines)

  submitting.value = true
  try {
    await refreshBundle()
    await validateCartStockBeforeSubmit(event.value.id, stockLines)
  } catch (e: unknown) {
    if (isApiError(e) && e.status === 409) {
      await refreshBundle()
      showToast(stockInsufficientMessage(e, getErrorMessage(e, 'Bestand nicht ausreichend.')), 'err')
    } else {
      showToast(getErrorMessage(e, 'Fehler'), 'err')
    }
    submitting.value = false
    return
  }

  try {
    const body: LocalOrderCreate = {
      client_order_id: newClientOrderId(),
      event_id: event.value.id,
      table_number: null,
      waiter_uuid: waiter.value?.uuid ?? null,
      order_source: 'cash_register',
      cash_register_uuid: String(register.value.uuid),
      lines: payloadLines,
      payments: [],
      voucher_print_via_bluetooth: false,
    }
    if (discountsEnabled.value && orderDiscount.value) {
      body.order_discount = orderDiscount.value
    }
    const res = await api<LocalOrderCreatedResponse>('/v1/orders', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    if (res.articles || res.ingredients) {
      patchEventStock(event.value.id, {
        articles: res.articles,
        ingredients: res.ingredients,
      })
    }
    clearCart()
    await router.push({
      name: 'register-pay',
      params: {
        registerUuid: String(register.value.uuid),
        orderId: String(res.local_order_id),
      },
    })
  } catch (e: unknown) {
    if (isApiError(e) && e.status === 409) {
      await refreshBundle()
      showToast(stockInsufficientMessage(e, getErrorMessage(e, 'Bestand nicht ausreichend.')), 'err')
    } else {
      showToast(getErrorMessage(e, 'Fehler'), 'err')
    }
  } finally {
    submitting.value = false
  }
}

watch([lines, cartCount], () => syncDisplayToCart(), { deep: true })

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
.cart-half {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
