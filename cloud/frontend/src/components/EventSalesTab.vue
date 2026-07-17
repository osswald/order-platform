<template>
  <div class="event-sales-tab">
    <div class="section-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="loadReport">{{ $t('common.refresh') }}</v-btn>
    </div>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">{{ $t('common.loading') }}</p>
    <template v-else-if="report">
      <div class="sales-summary-section">
        <div class="summary-grid">
          <div class="summary-card">
            <span class="summary-label">{{ $t('events.tabs.orders') }}</span>
            <span class="summary-value">{{ report.totals.distinct_orders_count }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ $t('events.tabs.lineValue') }}</span>
            <span class="summary-value">{{ formatMoney(report.totals.line_cents) }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ $t('events.tabs.paid') }}</span>
            <span class="summary-value">{{ formatMoney(report.totals.paid_cents) }}</span>
          </div>
          <div class="summary-card">
            <span class="summary-label">{{ $t('events.tabs.open') }}</span>
            <span class="summary-value">{{ formatMoney(report.totals.open_cents) }}</span>
          </div>
        </div>
      </div>

      <div class="sales-table-block">
        <h3 class="section-title">{{ $t('events.tabs.salesByWaiter') }}</h3>
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
        <h3 class="section-title">{{ $t('events.tabs.salesByStation') }}</h3>
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
        <h3 class="section-title">{{ $t('events.tabs.salesByArticle') }}</h3>
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
        <h3 class="section-title">{{ $t('events.tabs.salesByPayment') }}</h3>
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

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import { formatMoney as formatMoneyWithCurrency } from '../utils/money'
import VqDataTable from './VqDataTable.vue'
import type { EventSalesReportV3Read } from '@/types/api'
import { getErrorMessage } from '@/types/api'
import type { DataTableHeader } from '@/types/vuetify'

const { t } = useI18n()

const props = defineProps<{ eventId: number }>()
const loading = ref(true)
const loadError = ref('')
const report = ref<EventSalesReportV3Read | null>(null)

const COL_LABEL = { align: 'start' as const, minWidth: '12rem' }
const COL_MID = { align: 'end' as const, width: '6.5rem' }
const COL_LINE = { align: 'end' as const, width: '10.5rem' }
const COL_PAID = { align: 'end' as const, width: '10.5rem' }
const COL_PAD = { title: '', key: '_pad', align: 'end' as const, width: '10.5rem', sortable: false }

const waiterHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.waiter'), key: 'name', ...COL_LABEL },
  { title: t('events.tabs.orders'), key: 'order_count', ...COL_MID, sortable: true },
  { title: t('events.tabs.lineValue'), key: 'line_cents', ...COL_LINE },
  { title: t('events.tabs.paid'), key: 'paid_cents', ...COL_PAID },
])
const stationHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.station'), key: 'name', ...COL_LABEL },
  { title: t('events.tabs.quantity'), key: 'qty', ...COL_MID, sortable: true },
  { title: t('events.tabs.lineValue'), key: 'line_cents', ...COL_LINE },
  { ...COL_PAD },
])
const articleHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.article'), key: 'name', ...COL_LABEL },
  { title: t('events.tabs.quantity'), key: 'qty', ...COL_MID, sortable: true },
  { title: t('events.tabs.lineValue'), key: 'line_cents', ...COL_LINE },
  { ...COL_PAD },
])
const paymentHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.paymentType'), key: 'label', ...COL_LABEL },
  { title: '', key: '_pad_mid', ...COL_MID, sortable: false },
  { title: '', key: '_pad_line', ...COL_LINE, sortable: false },
  { title: t('events.tabs.amount'), key: 'amount_cents', ...COL_PAID },
])

function formatMoney(cents: number | null | undefined): string {
  return formatMoneyWithCurrency(cents, report.value?.currency || 'CHF', report.value?.country_code)
}

async function loadReport() {
  if (!props.eventId) return
  loading.value = true
  loadError.value = ''
  try {
    report.value = await apiJson<EventSalesReportV3Read>(
      `/events/${props.eventId}/sales-report-v3`,
    )
  } catch (e: unknown) {
    loadError.value = getErrorMessage(e, t('events.tabs.loadFailed'))
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
