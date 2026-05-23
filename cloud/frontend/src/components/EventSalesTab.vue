<template>
  <div class="event-sales-tab">
    <div class="section-toolbar">
      <Button
        label="Aktualisieren"
        type="button"
        class="secondary-button"
        :disabled="loading"
        @click="loadReport"
      />
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
      <DataTable
        v-else
        v-model:expandedRows="expandedRows"
        :value="report.orders"
        dataKey="id"
        class="list-table nested"
        responsiveLayout="scroll"
      >
        <Column expander style="width: 3rem" />
        <Column header="Bestell-Nr.">
          <template #body="{ data }">{{ data.order_number != null ? `#${data.order_number}` : '—' }}</template>
        </Column>
        <Column header="Zeit">
          <template #body="{ data }">{{ formatTime(data.ordered_at || data.created_at) }}</template>
        </Column>
        <Column field="table_number" header="Tisch" />
        <Column field="waiter_name" header="Kellner" />
        <Column header="Status">
          <template #body="{ data }">{{ statusLabel(data.payment_status) }}</template>
        </Column>
        <Column header="Positionen" style="text-align: right">
          <template #body="{ data }">{{ formatAmount(data.line_cents) }}</template>
        </Column>
        <Column header="Bezahlt" style="text-align: right">
          <template #body="{ data }">{{ formatAmount(data.paid_cents) }}</template>
        </Column>
        <template #expansion="{ data }">
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
                <template v-for="(line, idx) in data.lines" :key="idx">
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
            <p v-if="data.payments?.length" class="payments-line muted small">
              Zahlungen:
              <span v-for="(p, pi) in data.payments" :key="pi">
                {{ p.type_label }} {{ formatAmount(p.amount_cents) }}<span v-if="pi < data.payments.length - 1"> · </span>
              </span>
            </p>
          </div>
        </template>
      </DataTable>

      <h3 class="section-title">Umsatz nach Kellner</h3>
      <DataTable
        :value="report.by_waiter"
        class="list-table nested"
        responsiveLayout="scroll"
      >
        <Column field="name" header="Kellner" />
        <Column field="order_count" header="Bestellungen" />
        <Column header="Positionswert" style="text-align: right">
          <template #body="{ data }">{{ formatAmount(data.line_cents) }}</template>
        </Column>
        <Column header="Bezahlt" style="text-align: right">
          <template #body="{ data }">{{ formatAmount(data.paid_cents) }}</template>
        </Column>
      </DataTable>

      <h3 class="section-title">Umsatz nach Station</h3>
      <DataTable
        :value="report.by_station"
        class="list-table nested"
        responsiveLayout="scroll"
      >
        <Column field="name" header="Station" />
        <Column field="qty" header="Menge" />
        <Column header="Positionswert" style="text-align: right">
          <template #body="{ data }">{{ formatAmount(data.line_cents) }}</template>
        </Column>
      </DataTable>

      <h3 class="section-title">Umsatz nach Artikel</h3>
      <DataTable
        :value="report.by_article"
        class="list-table nested"
        responsiveLayout="scroll"
      >
        <Column field="name" header="Artikel" />
        <Column field="qty" header="Menge" />
        <Column header="Positionswert" style="text-align: right">
          <template #body="{ data }">{{ formatAmount(data.line_cents) }}</template>
        </Column>
      </DataTable>

      <h3 class="section-title">Umsatz nach Zahlungsart</h3>
      <DataTable
        :value="report.by_payment_type"
        class="list-table nested"
        responsiveLayout="scroll"
      >
        <Column field="label" header="Zahlungsart" />
        <Column header="Betrag" style="text-align: right">
          <template #body="{ data }">{{ formatAmount(data.amount_cents) }}</template>
        </Column>
      </DataTable>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import { apiFetch } from '../api'
import { formatAmount } from '../utils/money'

const props = defineProps({
  eventId: {
    type: Number,
    required: true,
  },
})

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
  margin-bottom: 0.75rem;
}
.footnote {
  margin: 0 0 1rem;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.summary-card {
  background: var(--surface-100, #f1f5f9);
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.summary-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary, #64748b);
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
  border-bottom: 1px solid var(--surface-200, #e2e8f0);
}
.lines-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.addition-row td {
  font-size: 0.85rem;
  color: var(--text-color-secondary, #64748b);
}
.payments-line {
  margin: 0.5rem 0 0;
}
.small {
  font-size: 0.8rem;
}
.error {
  color: var(--red-500, #ef4444);
}
</style>
