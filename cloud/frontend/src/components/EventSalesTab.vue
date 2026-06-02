<template>
  <div class="event-sales-tab">
    <div class="section-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="loadReport">Aktualisieren</v-btn>
    </div>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else-if="report">
      <div class="sales-summary-section">
        <div class="summary-grid">
          <div class="summary-card">
            <span class="summary-label">Bestellungen</span>
            <span class="summary-value">{{ report.totals.distinct_orders_count }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">Positionswert</span>
            <span class="summary-value">{{ formatMoney(report.totals.line_cents) }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">Bezahlt</span>
            <span class="summary-value">{{ formatMoney(report.totals.paid_cents) }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">Offen</span>
            <span class="summary-value">{{ formatMoney(report.totals.open_cents) }}</span>
          </div>
        </div>
      </div>

      <div class="sales-table-block">
        <h3 class="section-title">Umsatz nach Kellner</h3>
        <VqDataTable
          :headers="waiterHeaders"
          :items="report.by_waiter"
          hide-default-footer
          class="vq-data-table list-table nested sales-table"
        >
          <template #item.line_cents="{ item }">{{ formatMoney(item.line_cents) }}</template>
          <template #item.paid_cents="{ item }">{{ formatMoney(item.paid_cents) }}</template>
        </VqDataTable>
      </div>

      <div class="sales-table-block">
        <h3 class="section-title">Umsatz nach Station</h3>
        <VqDataTable
          :headers="stationHeaders"
          :items="report.by_station"
          hide-default-footer
          class="vq-data-table list-table nested sales-table"
        >
          <template #item.line_cents="{ item }">{{ formatMoney(item.line_cents) }}</template>
        </VqDataTable>
      </div>

      <div class="sales-table-block">
        <h3 class="section-title">Umsatz nach Artikel</h3>
        <VqDataTable
          :headers="articleHeaders"
          :items="report.by_article"
          hide-default-footer
          class="vq-data-table list-table nested sales-table"
        >
          <template #item.line_cents="{ item }">{{ formatMoney(item.line_cents) }}</template>
        </VqDataTable>
      </div>

      <div class="sales-table-block">
        <h3 class="section-title">Umsatz nach Zahlungsart</h3>
        <VqDataTable
          :headers="paymentHeaders"
          :items="report.by_payment_type"
          hide-default-footer
          class="vq-data-table list-table nested sales-table"
        >
          <template #item.amount_cents="{ item }">{{ formatMoney(item.amount_cents) }}</template>
        </VqDataTable>
      </div>
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

const COL_LABEL = { align: 'start', minWidth: '12rem' }
const COL_MID = { align: 'end', width: '6.5rem' }
const COL_LINE = { align: 'end', width: '10.5rem' }
const COL_PAID = { align: 'end', width: '10.5rem' }
const COL_PAD = { title: '', key: '_pad', align: 'end', width: '10.5rem', sortable: false }

const waiterHeaders = [
  { title: 'Kellner', key: 'name', ...COL_LABEL },
  { title: 'Bestellungen', key: 'order_count', ...COL_MID, sortable: true },
  { title: 'Positionswert', key: 'line_cents', ...COL_LINE },
  { title: 'Bezahlt', key: 'paid_cents', ...COL_PAID },
]
const stationHeaders = [
  { title: 'Station', key: 'name', ...COL_LABEL },
  { title: 'Menge', key: 'qty', ...COL_MID, sortable: true },
  { title: 'Positionswert', key: 'line_cents', ...COL_LINE },
  { ...COL_PAD },
]
const articleHeaders = [
  { title: 'Artikel', key: 'name', ...COL_LABEL },
  { title: 'Menge', key: 'qty', ...COL_MID, sortable: true },
  { title: 'Positionswert', key: 'line_cents', ...COL_LINE },
  { ...COL_PAD },
]
const paymentHeaders = [
  { title: 'Zahlungsart', key: 'label', ...COL_LABEL },
  { title: '', key: '_pad_mid', ...COL_MID, sortable: false },
  { title: '', key: '_pad_line', ...COL_LINE, sortable: false },
  { title: 'Betrag', key: 'amount_cents', ...COL_PAID },
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

<style scoped>
.section-toolbar {
  margin-bottom: 1rem;
}

.sales-summary-section {
  margin-bottom: 1.5rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: 0.75rem;
}

.summary-card {
  padding: 0.75rem 1rem;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-label {
  font-size: 0.8rem;
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.summary-value {
  font-size: 1.15rem;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.section-title {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}

.sales-table-block {
  margin-bottom: 1.25rem;
}

.sales-table-block:last-child {
  margin-bottom: 0;
}

.error {
  color: rgb(var(--v-theme-error));
  margin-bottom: 0.75rem;
}

.event-sales-tab :deep(.sales-table table) {
  table-layout: fixed;
  width: 100%;
}

.event-sales-tab :deep(.sales-table th),
.event-sales-tab :deep(.sales-table td) {
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-sales-tab :deep(.sales-table th:nth-child(1)),
.event-sales-tab :deep(.sales-table td:nth-child(1)) {
  width: auto;
}

.event-sales-tab :deep(.sales-table th:nth-child(2)),
.event-sales-tab :deep(.sales-table td:nth-child(2)) {
  width: 6.5rem;
}

.event-sales-tab :deep(.sales-table th:nth-child(3)),
.event-sales-tab :deep(.sales-table td:nth-child(3)) {
  width: 10.5rem;
}

.event-sales-tab :deep(.sales-table th:nth-child(4)),
.event-sales-tab :deep(.sales-table td:nth-child(4)) {
  width: 10.5rem;
}
</style>
