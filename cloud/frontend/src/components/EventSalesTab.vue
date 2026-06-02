<template>
  <div class="event-sales-tab">
    <div class="section-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="loadReport">Aktualisieren</v-btn>
    </div>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else-if="report">
      <div class="summary-grid">
        <div class="summary-card"><span class="summary-label">Bestellungen</span><span class="summary-value">{{ report.totals.distinct_orders_count }}</span></div>
        <div class="summary-card"><span class="summary-label">Positionswert</span><span class="summary-value">{{ formatMoney(report.totals.line_cents) }}</span></div>
        <div class="summary-card"><span class="summary-label">Bezahlt</span><span class="summary-value">{{ formatMoney(report.totals.paid_cents) }}</span></div>
        <div class="summary-card"><span class="summary-label">Offen</span><span class="summary-value">{{ formatMoney(report.totals.open_cents) }}</span></div>
      </div>
      <h3 class="section-title">Umsatz nach Kellner</h3>
      <VqDataTable :headers="waiterHeaders" :items="report.by_waiter" hide-default-footer class="vq-data-table list-table nested">
        <template #item.line_cents="{ item }">{{ formatMoney(item.line_cents) }}</template>
        <template #item.paid_cents="{ item }">{{ formatMoney(item.paid_cents) }}</template>
      </VqDataTable>
      <h3 class="section-title">Umsatz nach Station</h3>
      <VqDataTable :headers="stationHeaders" :items="report.by_station" hide-default-footer class="vq-data-table list-table nested">
        <template #item.line_cents="{ item }">{{ formatMoney(item.line_cents) }}</template>
      </VqDataTable>
      <h3 class="section-title">Umsatz nach Artikel</h3>
      <VqDataTable :headers="articleHeaders" :items="report.by_article" hide-default-footer class="vq-data-table list-table nested">
        <template #item.line_cents="{ item }">{{ formatMoney(item.line_cents) }}</template>
      </VqDataTable>
      <h3 class="section-title">Umsatz nach Zahlungsart</h3>
      <VqDataTable :headers="paymentHeaders" :items="report.by_payment_type" hide-default-footer class="vq-data-table list-table nested">
        <template #item.amount_cents="{ item }">{{ formatMoney(item.amount_cents) }}</template>
      </VqDataTable>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { apiFetch } from '../api'
import { formatAmount } from '../utils/money'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({ eventId: { type: Number, required: true } })
const loading = ref(true)
const loadError = ref('')
const report = ref(null)

const waiterHeaders = [
  { title: 'Kellner', key: 'name' },
  { title: 'Bestellungen', key: 'order_count', align: 'end' },
  { title: 'Positionswert', key: 'line_cents', align: 'end' },
  { title: 'Bezahlt', key: 'paid_cents', align: 'end' },
]
const stationHeaders = [
  { title: 'Station', key: 'name' },
  { title: 'Menge', key: 'qty', align: 'end' },
  { title: 'Positionswert', key: 'line_cents', align: 'end' },
]
const articleHeaders = [
  { title: 'Artikel', key: 'name' },
  { title: 'Menge', key: 'qty', align: 'end' },
  { title: 'Positionswert', key: 'line_cents', align: 'end' },
]
const paymentHeaders = [
  { title: 'Zahlungsart', key: 'label' },
  { title: 'Betrag', key: 'amount_cents', align: 'end' },
]

function formatMoney(cents) {
  const currency = report.value?.currency || 'CHF'
  return `${formatAmount(cents)} ${currency}`
}

async function loadReport() {
  if (!props.eventId) return
  loading.value = true
  loadError.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/sales-report-v3`)
    if (!resp.ok) throw new Error(await resp.text())
    report.value = await resp.json()
  } catch (e) {
    loadError.value = e.message || 'Laden fehlgeschlagen'
    report.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.eventId, loadReport, { immediate: true })
</script>
