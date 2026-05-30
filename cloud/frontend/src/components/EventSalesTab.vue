<template>
  <div class="event-sales-tab">
    <div class="section-toolbar">
      <v-btn
        variant="outlined"
        type="button"
        :disabled="loading"
        @click="loadReport"
      >
        Aktualisieren
      </v-btn>
    </div>

    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else-if="report">
      <p class="muted small footnote">
        Bestellungen = eindeutige Bestellnummern (FERTIG am Pi). Sync-Zeilen können mehrfach vorkommen.
        Preise aus Bestell-Snapshot, sonst aktuelle Artikelpreise.
      </p>

      <div class="summary-grid">
        <div class="summary-card">
          <span class="summary-label">Bestellungen</span>
          <span class="summary-value">{{ report.totals.distinct_orders_count ?? report.totals.orders_count }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Positionswert</span>
          <span class="summary-value">{{ formatAmount(report.totals.line_cents) }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Bezahlt</span>
          <span class="summary-value">{{ formatAmount(report.totals.paid_cents) }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">Offen</span>
          <span class="summary-value">{{ formatAmount(report.totals.open_cents) }}</span>
        </div>
      </div>

      <h3 class="section-title">Bestellungen</h3>
      <p v-if="!report.orders.length" class="muted">Noch keine Bestellungen von Pi synchronisiert.</p>
      <VqDataTable
        v-else
        v-model:expanded="expandedRows"
        :headers="orderHeaders"
        :items="report.orders"
        item-value="id"
        show-expand
        hide-default-footer
        class="vq-data-table list-table nested"
      >
        <template #item.order_number="{ item }">
          {{ item.order_number != null ? `#${item.order_number}` : '—' }}
        </template>
        <template #item.ordered_at="{ item }">{{ formatTime(item.ordered_at || item.created_at) }}</template>
        <template #item.payment_status="{ item }">{{ statusLabel(item.payment_status) }}</template>
        <template #item.line_cents="{ item }">{{ formatAmount(item.line_cents) }}</template>
        <template #item.paid_cents="{ item }">{{ formatAmount(item.paid_cents) }}</template>
        <template #expanded-row="{ columns, item }">
          <tr>
            <td :colspan="columns.length">
              <div class="expansion-panel">
                <table class="lines-table">
                  <thead>
                    <tr>
                      <th>Artikel</th>
                      <th>Menge</th>
                      <th>Station</th>
                      <th class="num">Betrag</th>
                    </tr>
                  </thead>
                  <tbody>
                    <template v-for="(line, idx) in item.lines" :key="idx">
                      <tr>
                        <td>{{ line.name }}</td>
                        <td>{{ line.qty }}</td>
                        <td>{{ line.station_name }}</td>
                        <td class="num">{{ formatAmount(line.line_cents) }}</td>
                      </tr>
                      <tr
                        v-for="add in line.additions"
                        :key="'add-' + idx + '-' + add.article_id"
                        class="addition-row"
                      >
                        <td colspan="2">+ {{ add.name }} ({{ add.qty }})</td>
                        <td></td>
                        <td class="num">{{ formatAmount(add.line_cents) }}</td>
                      </tr>
                    </template>
                  </tbody>
                </table>
                <p v-if="item.payments?.length" class="payments-line muted small">
                  Zahlungen:
                  <span v-for="(p, pi) in item.payments" :key="pi">
                    {{ p.type_label }} {{ formatAmount(p.amount_cents) }}<span v-if="pi < item.payments.length - 1"> · </span>
                  </span>
                </p>
              </div>
            </td>
          </tr>
        </template>
      </VqDataTable>

      <h3 class="section-title">Umsatz nach Kellner</h3>
      <VqDataTable
        :headers="waiterHeaders"
        :items="report.by_waiter"
        hide-default-footer
        class="vq-data-table list-table nested"
      >
        <template #item.line_cents="{ item }">{{ formatAmount(item.line_cents) }}</template>
        <template #item.paid_cents="{ item }">{{ formatAmount(item.paid_cents) }}</template>
      </VqDataTable>

      <h3 class="section-title">Umsatz nach Station</h3>
      <VqDataTable
        :headers="stationHeaders"
        :items="report.by_station"
        hide-default-footer
        class="vq-data-table list-table nested"
      >
        <template #item.line_cents="{ item }">{{ formatAmount(item.line_cents) }}</template>
      </VqDataTable>

      <h3 class="section-title">Umsatz nach Artikel</h3>
      <VqDataTable
        :headers="articleHeaders"
        :items="report.by_article"
        hide-default-footer
        class="vq-data-table list-table nested"
      >
        <template #item.line_cents="{ item }">{{ formatAmount(item.line_cents) }}</template>
      </VqDataTable>

      <h3 class="section-title">Umsatz nach Zahlungsart</h3>
      <VqDataTable
        :headers="paymentHeaders"
        :items="report.by_payment_type"
        hide-default-footer
        class="vq-data-table list-table nested"
      >
        <template #item.amount_cents="{ item }">{{ formatAmount(item.amount_cents) }}</template>
      </VqDataTable>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { apiFetch } from '../api'
import { formatAmount } from '../utils/money'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({
  eventId: {
    type: Number,
    required: true,
  },
})

const orderHeaders = [
  { title: 'Bestell-Nr.', key: 'order_number', sortable: false },
  { title: 'Zeit', key: 'ordered_at', sortable: false },
  { title: 'Tisch', key: 'table_number' },
  { title: 'Kellner', key: 'waiter_name' },
  { title: 'Status', key: 'payment_status', sortable: false },
  { title: 'Positionen', key: 'line_cents', align: 'end' },
  { title: 'Bezahlt', key: 'paid_cents', align: 'end' },
]

const waiterHeaders = [
  { title: 'Kellner', key: 'name' },
  { title: 'Bestellungen', key: 'order_count' },
  { title: 'Positionswert', key: 'line_cents', align: 'end' },
  { title: 'Bezahlt', key: 'paid_cents', align: 'end' },
]

const stationHeaders = [
  { title: 'Station', key: 'name' },
  { title: 'Menge', key: 'qty' },
  { title: 'Positionswert', key: 'line_cents', align: 'end' },
]

const articleHeaders = [
  { title: 'Artikel', key: 'name' },
  { title: 'Menge', key: 'qty' },
  { title: 'Positionswert', key: 'line_cents', align: 'end' },
]

const paymentHeaders = [
  { title: 'Zahlungsart', key: 'label' },
  { title: 'Betrag', key: 'amount_cents', align: 'end' },
]

const loading = ref(true)
const loadError = ref('')
const report = ref(null)
const expandedRows = ref([])

function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}

function statusLabel(status) {
  const s = String(status || '').toLowerCase()
  if (s === 'paid') return 'Bezahlt'
  if (s === 'open') return 'Offen'
  return status || '—'
}

async function loadReport() {
  if (!props.eventId) return
  loading.value = true
  loadError.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/sales-report`)
    if (!resp.ok) throw new Error(await resp.text())
    report.value = await resp.json()
    expandedRows.value = []
  } catch (e) {
    loadError.value = e.message || 'Laden fehlgeschlagen'
    report.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => props.eventId,
  () => {
    loadReport()
  },
  { immediate: true },
)
</script>

<style scoped>
.section-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.footnote {
  margin: 0 0 1rem;
}
.muted {
  opacity: 0.7;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.summary-card {
  background: rgba(var(--v-theme-on-surface), 0.04);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.summary-label {
  font-size: 0.8rem;
  opacity: 0.7;
}
.summary-value {
  font-size: 1.15rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.section-title {
  font-size: 1rem;
  margin: 1.25rem 0 0.5rem;
}
.expansion-panel {
  padding: 0.5rem 0.75rem 0.75rem;
}
.lines-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.lines-table th,
.lines-table td {
  padding: 0.35rem 0.5rem;
  text-align: left;
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.lines-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.addition-row td {
  font-size: 0.85rem;
  opacity: 0.7;
}
.payments-line {
  margin: 0.5rem 0 0;
}
.small {
  font-size: 0.8rem;
}

@media (max-width: 992px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
