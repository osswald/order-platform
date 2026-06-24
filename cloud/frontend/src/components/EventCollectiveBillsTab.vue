<template>
  <div class="event-collective-tab">
    <div class="section-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="load">{{ $t('common.refresh') }}</v-btn>
    </div>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">{{ $t('common.loading') }}</p>
    <template v-else-if="data">
      <p v-if="!data.collective_bills.length" class="muted">{{ $t('events.tabs.noCollectiveBills') }}</p>
      <v-expansion-panels v-else class="collective-panels" variant="accordion">
        <v-expansion-panel v-for="bill in data.collective_bills" :key="bill.uuid" :value="bill.uuid">
          <v-expansion-panel-title>
            <div class="panel-title">
              <span class="panel-name">{{ bill.name }}</span>
              <v-chip size="small" :color="statusChipColor(bill.status)" variant="tonal" class="panel-status">
                {{ statusLabel(bill.status) }}
              </v-chip>
              <span class="panel-meta muted">
                {{ $t('events.tabs.orderCountMeta', { count: bill.order_count, total: formatMoney(bill.line_cents) }) }}
                <template v-if="bill.open_cents > 0">
                  · {{ $t('events.tabs.openAmount', { amount: formatMoney(bill.open_cents) }) }}
                </template>
              </span>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="bill-summary">
              <div class="summary-grid">
                <div class="summary-card">
                  <span class="summary-label">{{ $t('events.tabs.orders') }}</span>
                  <span class="summary-value">{{ bill.order_count }}</span>
                </div>
                <div class="summary-card">
                  <span class="summary-label">{{ $t('events.tabs.totalAmount') }}</span>
                  <span class="summary-value">{{ formatMoney(bill.line_cents) }}</span>
                </div>
                <div class="summary-card">
                  <span class="summary-label">{{ $t('events.tabs.open') }}</span>
                  <span class="summary-value">{{ formatMoney(bill.open_cents) }}</span>
                </div>
                <div class="summary-card">
                  <span class="summary-label">{{ $t('events.tabs.paid') }}</span>
                  <span class="summary-value">{{ formatMoney(bill.paid_cents) }}</span>
                </div>
              </div>
              <p v-if="bill.created_at || bill.closed_at" class="bill-times muted">
                <span v-if="bill.created_at">{{ $t('events.tabs.createdAt', { time: formatTime(bill.created_at) }) }}</span>
                <span v-if="bill.closed_at"> · {{ $t('events.tabs.closedAt', { time: formatTime(bill.closed_at) }) }}</span>
              </p>
            </div>

            <p v-if="!positionRows(bill).length" class="muted">{{ $t('events.tabs.noPositions') }}</p>
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

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import { formatAmount } from '../utils/money'
import VqDataTable from './VqDataTable.vue'
import type { CollectiveBillRead, EventCollectiveBillsListRead } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import type { CollectiveBillLineGroup, CollectiveBillPositionRow } from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'

const { t } = useI18n()

const props = defineProps<{ eventId: number }>()

const positionHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.article'), key: 'name' },
  { title: t('events.tabs.quantity'), key: 'qty', align: 'end' },
  { title: t('events.tabs.amount'), key: 'line_cents', align: 'end' },
])

const loading = ref(false)
const loadError = ref('')
const data = ref<EventCollectiveBillsListRead | null>(null)

function formatMoney(cents: number | null | undefined): string {
  return `${formatAmount(cents)} ${data.value?.currency || 'CHF'}`
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return t('common.emDash')
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}

function statusLabel(v: string | null | undefined): string {
  const s = String(v || '').toLowerCase()
  if (s === 'closed' || s === 'paid') return t('events.tabs.statusClosed')
  if (s === 'open') return t('events.tabs.statusOpen')
  return v || t('common.emDash')
}

function statusChipColor(v: string | null | undefined): string {
  const s = String(v || '').toLowerCase()
  if (s === 'closed' || s === 'paid') return 'success'
  if (s === 'open') return 'warning'
  return 'default'
}

function positionRows(bill: CollectiveBillRead): CollectiveBillPositionRow[] {
  const groups = (bill.line_groups || []) as CollectiveBillLineGroup[]
  return groups.map((g, i) => ({
    rowKey: `${g.article_id}-${i}`,
    name: g.name || t('common.emDash'),
    additions: g.additions || [],
    qty: g.total_qty ?? 1,
    line_cents: g.line_total_cents ?? 0,
  }))
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    data.value = await apiJson<EventCollectiveBillsListRead>(
      `/events/${props.eventId}/collective-bills`,
    )
  } catch (e: unknown) {
    loadError.value = getErrorMessage(e, t('events.tabs.loadFailed'))
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
