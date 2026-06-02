<template>
  <div class="event-collective-tab">
    <div class="section-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="load">Aktualisieren</v-btn>
    </div>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">Laden…</p>
    <template v-else-if="data">
      <p v-if="!data.collective_bills.length" class="muted">Noch keine Sammelrechnungen synchronisiert.</p>
      <v-expansion-panels v-else class="collective-panels" variant="accordion">
        <v-expansion-panel v-for="bill in data.collective_bills" :key="bill.uuid" :value="bill.uuid">
          <v-expansion-panel-title>
            <div class="panel-title">
              <span class="panel-name">{{ bill.name }}</span>
              <v-chip size="small" :color="statusChipColor(bill.status)" variant="tonal" class="panel-status">
                {{ statusLabel(bill.status) }}
              </v-chip>
              <span class="panel-meta muted">
                {{ bill.order_count }} Bestellung(en) · {{ formatMoney(bill.line_cents) }}
                <template v-if="bill.open_cents > 0"> · offen {{ formatMoney(bill.open_cents) }}</template>
              </span>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="bill-summary">
              <div class="summary-grid">
                <div class="summary-card">
                  <span class="summary-label">Bestellungen</span>
                  <span class="summary-value">{{ bill.order_count }}</span>
                </div>
                <div class="summary-card">
                  <span class="summary-label">Gesamtbetrag</span>
                  <span class="summary-value">{{ formatMoney(bill.line_cents) }}</span>
                </div>
                <div class="summary-card">
                  <span class="summary-label">Offen</span>
                  <span class="summary-value">{{ formatMoney(bill.open_cents) }}</span>
                </div>
                <div class="summary-card">
                  <span class="summary-label">Bezahlt</span>
                  <span class="summary-value">{{ formatMoney(bill.paid_cents) }}</span>
                </div>
              </div>
              <p v-if="bill.created_at || bill.closed_at" class="bill-times muted">
                <span v-if="bill.created_at">Erstellt: {{ formatTime(bill.created_at) }}</span>
                <span v-if="bill.closed_at"> · Abgeschlossen: {{ formatTime(bill.closed_at) }}</span>
              </p>
            </div>

            <p v-if="!positionRows(bill).length" class="muted">Noch keine Posten.</p>
            <VqDataTable
              v-else
              :headers="positionHeaders"
              :items="positionRows(bill)"
              item-value="rowKey"
              hide-default-footer
              class="vq-data-table list-table nested positions-table"
            >
              <template #item.name="{ item }">
                <div class="name-cell">
                  <span>{{ item.name }}</span>
                  <span v-for="add in item.additions" :key="add.article_id" class="addition-name">
                    + {{ add.name }}
                  </span>
                </div>
              </template>
              <template #item.qty="{ item }">{{ item.qty }}</template>
              <template #item.line_cents="{ item }">{{ formatMoney(item.line_cents) }}</template>
            </VqDataTable>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { apiFetch } from '../api'
import { formatAmount } from '../utils/money'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({ eventId: { type: Number, required: true } })

const positionHeaders = [
  { title: 'Artikel', key: 'name' },
  { title: 'Menge', key: 'qty', align: 'end' },
  { title: 'Betrag', key: 'line_cents', align: 'end' },
]

const loading = ref(false)
const loadError = ref('')
const data = ref(null)

function formatMoney(cents) {
  return `${formatAmount(cents)} ${data.value?.currency || 'CHF'}`
}

function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}

function statusLabel(v) {
  const s = String(v || '').toLowerCase()
  if (s === 'closed' || s === 'paid') return 'Abgeschlossen'
  if (s === 'open') return 'Offen'
  return v || '—'
}

function statusChipColor(v) {
  const s = String(v || '').toLowerCase()
  if (s === 'closed' || s === 'paid') return 'success'
  if (s === 'open') return 'warning'
  return 'default'
}

function positionRows(bill) {
  return (bill.line_groups || []).map((g, i) => ({
    rowKey: `${g.article_id}-${i}`,
    name: g.name || '—',
    additions: g.additions || [],
    qty: g.total_qty ?? 1,
    line_cents: g.line_total_cents ?? 0,
  }))
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/collective-bills`)
    if (!resp.ok) throw new Error(await resp.text())
    data.value = await resp.json()
  } catch (e) {
    loadError.value = e.message || 'Laden fehlgeschlagen'
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.eventId, load, { immediate: true })
</script>

<style scoped>
.section-toolbar {
  margin-bottom: 1rem;
}

.error {
  color: rgb(var(--v-theme-error));
  margin-bottom: 0.75rem;
}

.collective-panels {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

.panel-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  width: 100%;
  padding-right: 0.5rem;
}

.panel-name {
  font-weight: 600;
}

.panel-meta {
  font-size: 0.85rem;
}

.bill-summary {
  margin-bottom: 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.summary-card {
  padding: 0.6rem 0.75rem;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.summary-label {
  font-size: 0.75rem;
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.summary-value {
  font-size: 1rem;
  font-weight: 600;
}

.bill-times {
  font-size: 0.85rem;
  margin: 0;
}

.name-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.addition-name {
  font-size: 0.85rem;
  opacity: 0.85;
}

.positions-table {
  margin-top: 0.25rem;
}
</style>
