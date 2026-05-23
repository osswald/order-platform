<template>
  <div class="split-pay-screen">
    <SplitPayHeader :table="table" @back="router.push({ name: 'hub' })" />

    <p v-if="loading" class="muted state-msg">Laden…</p>
    <template v-else-if="!groups.length">
      <div class="state-msg">
        <p>Keine offenen Posten auf diesem Tisch.</p>
        <button type="button" class="btn primary" @click="router.push({ name: 'hub' })">Zurück</button>
      </div>
    </template>
    <template v-else>
      <div class="split-body">
        <section class="panel top-panel">
          <ul class="line-list">
            <SplitPayLineRow
              v-for="g in topGroups"
              :key="g.key"
              variant="top"
              :name="g.name"
              :addition-labels="g.additionLabels"
              :basket-qty="g.basketQty"
              :total-qty="g.totalQty"
              :unit-cents="g.unitCents"
              @tap-qty="openQtyModal(g)"
              @tap-name="bumpBasket(g, 1)"
              @tap-price="bumpBasket(g, -1)"
            />
          </ul>
          <p v-if="!topGroups.length" class="muted empty-hint">
            Unten „↑“ oder Zeilen antippen für Teilzahlung
          </p>
        </section>

        <div class="bar bar-green">
          <button
            type="button"
            class="bar-side"
            :disabled="!basketItemCount"
            aria-label="Alle Positionen nach unten"
            @click="moveAllToBottom"
          >
            {{ basketItemCount }} ↓
          </button>
          <button
            type="button"
            class="bar-main"
            :disabled="!basketCents || paying"
            @click="onGreenCheck"
          >
            Teilbetrag {{ formatAmount(basketCents) }}
            <span class="check" aria-hidden="true">✓</span>
          </button>
        </div>

        <section class="panel bottom-panel">
          <ul class="line-list">
            <SplitPayLineRow
              v-for="g in bottomGroups"
              :key="g.key"
              variant="bottom"
              :name="g.name"
              :addition-labels="g.additionLabels"
              :basket-qty="g.basketQty"
              :total-qty="g.totalQty"
              :unit-cents="g.unitCents"
              @tap-row="bumpBasket(g, 1)"
            />
          </ul>
        </section>
      </div>

      <div class="bar bar-red">
        <button
          type="button"
          class="bar-side"
          :disabled="!remainingItemCount"
          aria-label="Alle Positionen nach oben"
          @click="moveAllToTop"
        >
          {{ remainingItemCount }} ↑
        </button>
        <span class="bar-main">Rest {{ formatAmount(restCents) }} / {{ formatAmount(totalCents) }}</span>
        <button type="button" class="bar-side cancel" aria-label="Abbrechen" @click="router.push({ name: 'hub' })">
          ✕
        </button>
      </div>
    </template>

    <QtyInputModal
      :open="qtyModalOpen"
      :name="qtyModalGroup?.name || ''"
      :max="qtyModalGroup?.totalQty || 0"
      :model-value="qtyModalGroup?.basketQty || 0"
      @close="qtyModalOpen = false"
      @confirm="onQtyConfirm"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as store from '../store'
import { api } from '../api'
import { formatAmount } from '../utils/money'
import { lineAdditionLabels } from '../utils/bundleHelpers'
import { buildPayment } from '../utils/paymentTypes'
import { pickPaymentType } from '../utils/pickPaymentType'
import SplitPayHeader from '../components/SplitPayHeader.vue'
import SplitPayLineRow from '../components/SplitPayLineRow.vue'
import QtyInputModal from '../components/QtyInputModal.vue'

const route = useRoute()
const router = useRouter()
const summary = ref(null)
const groups = ref([])
const loading = ref(true)
const paying = ref(false)
const qtyModalOpen = ref(false)
const qtyModalGroup = ref(null)

const table = computed(() => parseInt(String(route.query.table), 10))
const event = computed(() => store.selectedEvent.value)
const paymentMode = computed(() => (event.value?.payment_mode || 'pay_later').toLowerCase())

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
  const ev = event.value
  if (!ev || !table.value) return
  summary.value = await api(`/v1/tables/${table.value}?event_id=${ev.id}`)
  initGroups(summary.value)
}

onMounted(async () => {
  loading.value = true
  try {
    await reload()
  } catch (e) {
    store.showToast(e.message || 'Laden fehlgeschlagen', 'err')
    router.replace({ name: 'hub' })
  } finally {
    loading.value = false
  }
})

async function settlePartial(payments) {
  paying.value = true
  try {
    const res = await api(`/v1/tables/${table.value}/settle-partial`, {
      method: 'POST',
      body: JSON.stringify({
        event_id: event.value.id,
        payments,
        selections: selectionsPayload(),
      }),
    })
    if (res.remaining_cents <= 0) {
      store.showToast('Tisch vollständig abgerechnet.', 'ok')
      router.replace({ name: 'hub' })
      return
    }
    store.showToast(`Teilbetrag bezahlt. Rest: ${formatAmount(res.remaining_cents)}`, 'ok')
    await reload()
  } catch (e) {
    store.showToast(e.message || 'Abrechnung fehlgeschlagen', 'err')
  } finally {
    paying.value = false
  }
}

async function onGreenCheck() {
  if (!basketCents.value) return
  try {
    const payments = await paymentsForAmount(basketCents.value)
    await settlePartial(payments)
  } catch {
    /* picker cancelled */
  }
}
</script>
