<template>
  <div class="event-collective-tab">
    <div class="section-toolbar">
      <v-btn
        variant="outlined"
        type="button"
        :disabled="loading"
        @click="load"
      >
        Aktualisieren
      </v-btn>
    </div>

    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else-if="data">
      <p class="muted small footnote">
        Bestellungen = eindeutige Bestellnummern (FERTIG am Pi). Mehrere Sync-Zeilen können dieselbe Nummer haben.
      </p>

      <p v-if="!data.collective_bills.length" class="muted">Noch keine Sammelrechnungen synchronisiert.</p>
      <VqDataTable
        v-else
        v-model:expanded="expandedBillRows"
        :headers="billHeaders"
        :items="data.collective_bills"
        item-value="uuid"
        show-expand
        hide-default-footer
        class="vq-data-table list-table nested"
      >
        <template #item.status="{ item }">{{ statusLabel(item.status) }}</template>
        <template #item.order_count="{ item }">{{ item.order_count }}</template>
        <template #item.open_cents="{ item }">{{ formatAmount(item.open_cents) }}</template>
        <template #item.paid_cents="{ item }">{{ formatAmount(item.paid_cents) }}</template>
        <template #item.created_at="{ item }">{{ formatTime(item.created_at) }}</template>
        <template #expanded-row="{ columns, item: bill }">
          <tr>
            <td :colspan="columns.length">
              <div class="expansion-panel">
                <p v-if="!bill.orders.length" class="muted">Keine Bestellungen.</p>
                <div v-for="order in bill.orders" :key="order.id" class="order-block">
                  <div class="order-header">
                    <span class="order-title">
                      {{ order.order_number != null ? `Bestellung #${order.order_number}` : 'Bestellung' }}
                    </span>
                    <span class="order-meta muted small">
                      {{ formatTime(order.ordered_at || order.created_at) }}
                      · {{ statusLabel(order.payment_status) }}
                      · {{ formatAmount(order.line_cents) }}
                    </span>
                  </div>
                  <p v-if="!order.lines?.length" class="muted small">Keine Positionen.</p>
                  <table v-else class="lines-table">
                    <thead>
                      <tr>
                        <th>Artikel</th>
                        <th>Menge</th>
                        <th class="num">Betrag</th>
                      </tr>
                    </thead>
                    <tbody>
                      <template v-for="(line, idx) in order.lines" :key="idx">
                        <tr>
                          <td>
                            {{ line.name }}
                            <span v-if="line.note" class="line-note"> — {{ line.note }}</span>
                          </td>
                          <td>{{ line.qty }}</td>
                          <td class="num">{{ formatAmount(line.line_cents) }}</td>
                        </tr>
                        <tr
                          v-for="add in line.additions"
                          :key="'add-' + idx + '-' + add.article_id"
                          class="addition-row"
                        >
                          <td colspan="2">+ {{ add.name }} ({{ add.qty }})</td>
                          <td class="num">{{ formatAmount(add.line_cents) }}</td>
                        </tr>
                      </template>
                    </tbody>
                  </table>
                  <p v-if="order.payments?.length" class="payments-line muted small">
                    Zahlungen:
                    <span v-for="(p, pi) in order.payments" :key="pi">
                      {{ paymentLabel(p) }} {{ formatAmount(p.amount_cents) }}<span v-if="pi < order.payments.length - 1"> · </span>
                    </span>
                  </p>
                  <p class="sync-id muted small">Sync-ID: {{ order.client_order_id }}</p>
                </div>
              </div>
            </td>
          </tr>
        </template>
      </VqDataTable>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { apiFetch } from '../api'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({
  eventId: { type: Number, required: true },
})

const billHeaders = [
  { title: 'Name', key: 'name' },
  { title: 'Status', key: 'status', sortable: false },
  { title: 'Bestellungen', key: 'order_count', align: 'end' },
  { title: 'Offen', key: 'open_cents', align: 'end' },
  { title: 'Bezahlt', key: 'paid_cents', align: 'end' },
  { title: 'Erstellt', key: 'created_at', sortable: false },
]

const loading = ref(false)
const loadError = ref('')
const data = ref(null)
const expandedBillRows = ref([])

function formatAmount(cents) {
  const c = Number(cents) || 0
  return `${(c / 100).toFixed(2)} ${data.value?.currency || 'CHF'}`
}

function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}

function statusLabel(s) {
  const v = (s || '').toLowerCase()
  if (v === 'paid') return 'Bezahlt'
  if (v === 'closed') return 'Abgeschlossen'
  if (v === 'open') return 'Offen'
  return s || '—'
}

const PAYMENT_LABELS = {
  cash: 'Bargeld',
  twint: 'TWINT',
  sumup: 'SumUp',
  stripe_terminal: 'Karte',
  instant: 'Sofort',
}

function paymentLabel(p) {
  const t = (p?.type || '').toLowerCase()
  return PAYMENT_LABELS[t] || t || 'Zahlung'
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/collective-bills`)
    if (!resp.ok) throw new Error(await resp.text())
    data.value = await resp.json()
    expandedBillRows.value = []
  } catch (e) {
    loadError.value = e.message || 'Laden fehlgeschlagen'
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.eventId, load)
</script>

<style scoped>
.section-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.footnote {
  margin-bottom: 1rem;
}
.muted {
  opacity: 0.7;
}
.expansion-panel {
  padding: 0.5rem 0.75rem 0.75rem;
}
.order-block {
  padding: 0.75rem 0;
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.order-block:last-child {
  border-bottom: none;
}
.order-header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem 1rem;
  margin-bottom: 0.5rem;
}
.order-title {
  font-weight: 600;
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
.line-note {
  opacity: 0.7;
  font-size: 0.85rem;
}
.payments-line,
.sync-id {
  margin: 0.5rem 0 0;
}
.small {
  font-size: 0.8rem;
}

@media (max-width: 992px) {
  .order-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}
</style>
