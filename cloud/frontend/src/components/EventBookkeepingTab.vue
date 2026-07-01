<template>
  <div class="event-bookkeeping-tab">
    <div class="section-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="loadReport">{{ $t('common.refresh') }}</v-btn>
    </div>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <p v-else-if="loading" class="muted">{{ $t('common.loading') }}</p>
    <template v-else-if="report">
      <div v-if="report.warnings?.length" class="warnings">
        <p v-for="(w, i) in report.warnings" :key="i" class="warning">{{ w }}</p>
      </div>

      <div class="sales-table-block">
        <h3 class="section-title">{{ $t('events.tabs.bookkeepingSummary') }}</h3>
        <VqDataTable
          :headers="summaryHeaders"
          :items="report.summary || []"
          hide-default-footer
          class="vq-data-table list-table nested sales-table"
        >
          <template #item.debit_account="{ item }">{{ accountLabel(item.debit_account) }}</template>
          <template #item.credit_account="{ item }">{{ accountLabel(item.credit_account) }}</template>
          <template #item.tax_code="{ item }">{{ taxLabel(item.tax_code) }}</template>
          <template #item.net_cents="{ item }">{{ formatMoney(item.net_cents) }}</template>
          <template #item.vat_cents="{ item }">{{ formatMoney(item.vat_cents) }}</template>
          <template #item.gross_cents="{ item }">{{ formatMoney(item.gross_cents) }}</template>
          <template #item.subsidiary="{ item }">{{ subsidiaryLabel(item) }}</template>
          <template #item.collective_bill_name="{ item }">{{ item.collective_bill_name || '—' }}</template>
        </VqDataTable>
      </div>

      <div class="sales-table-block">
        <h3 class="section-title">{{ $t('events.tabs.bookkeepingDetail') }}</h3>
        <div v-if="!report.detail?.length" class="muted">{{ $t('events.tabs.bookkeepingNoDetail') }}</div>
        <div v-for="entry in report.detail || []" :key="detailKey(entry)" class="detail-block">
          <h4 class="detail-title">{{ detailTitle(entry) }}</h4>
          <VqDataTable
            :headers="detailHeaders"
            :items="entry.lines || []"
            hide-default-footer
            class="vq-data-table list-table nested sales-table"
          >
            <template #item.side="{ item }">{{ sideLabel(item.side) }}</template>
            <template #item.account="{ item }">{{ accountLabel(item.account) }}</template>
            <template #item.amount_cents="{ item }">{{ formatMoney(item.amount_cents) }}</template>
            <template #item.tax_code="{ item }">{{ taxLabel(item.tax_code) }}</template>
            <template #item.subsidiary="{ item }">{{ subsidiaryLineLabel(item) }}</template>
          </VqDataTable>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiJson } from '../api'
import { formatMoney as formatMoneyWithCurrency } from '../utils/money'
import VqDataTable from './VqDataTable.vue'
import { getErrorMessage } from '@/types/api'
import type {
  BookkeepingAccountRef,
  BookkeepingDetailEntry,
  BookkeepingDetailLine,
  BookkeepingSummaryRow,
  BookkeepingTaxCodeRef,
  EventBookkeepingReport,
} from '@/types/ui'
import type { DataTableHeader } from '@/types/vuetify'

const props = withDefaults(
  defineProps<{
    eventId: number
    currency?: string
    countryCode?: string
  }>(),
  {
    currency: 'CHF',
    countryCode: 'CH',
  },
)

const { t } = useI18n()
const loading = ref(false)
const loadError = ref('')
const report = ref<EventBookkeepingReport | null>(null)

const summaryHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.bookkeepingDebit'), key: 'debit_account' },
  { title: t('events.tabs.bookkeepingCredit'), key: 'credit_account' },
  { title: t('events.tabs.bookkeepingTaxCode'), key: 'tax_code' },
  { title: t('events.tabs.bookkeepingNet'), key: 'net_cents', align: 'end' },
  { title: t('events.tabs.bookkeepingVat'), key: 'vat_cents', align: 'end' },
  { title: t('events.tabs.bookkeepingGross'), key: 'gross_cents', align: 'end' },
  { title: t('events.tabs.bookkeepingSubsidiary'), key: 'subsidiary' },
  { title: t('events.tabs.bookkeepingCollectiveBill'), key: 'collective_bill_name' },
])

const detailHeaders = computed((): DataTableHeader[] => [
  { title: t('events.tabs.bookkeepingSide'), key: 'side' },
  { title: t('events.tabs.bookkeepingAccount'), key: 'account' },
  { title: t('events.tabs.bookkeepingAmount'), key: 'amount_cents', align: 'end' },
  { title: t('events.tabs.bookkeepingTaxCode'), key: 'tax_code' },
  { title: t('events.tabs.bookkeepingSubsidiary'), key: 'subsidiary' },
])

function formatMoney(cents: number | null | undefined): string {
  return formatMoneyWithCurrency(cents, props.currency || 'CHF', props.countryCode)
}

function accountLabel(account: BookkeepingAccountRef | null | undefined): string {
  if (!account) return '—'
  return `${account.number} ${account.name}`.trim()
}

function taxLabel(taxCode: BookkeepingTaxCodeRef | null | undefined): string {
  if (!taxCode?.name) return '—'
  const rate = taxCode.rate_percent != null ? ` (${taxCode.rate_percent}%)` : ''
  return `${taxCode.name}${rate}`
}

function subsidiaryLabel(item: BookkeepingSummaryRow): string {
  const code = item.subsidiary_code
  const name = item.subsidiary_name
  if (code && name) return `${code} · ${name}`
  return code || name || '—'
}

function subsidiaryLineLabel(item: BookkeepingDetailLine): string {
  const code = item.subsidiary_code
  const name = item.subsidiary_name
  if (code && name) return `${code} · ${name}`
  return code || name || '—'
}

function sideLabel(side: string | null | undefined): string {
  if (side === 'debit') return t('events.tabs.bookkeepingSoll')
  if (side === 'credit') return t('events.tabs.bookkeepingHaben')
  return side || '—'
}

function detailKey(entry: BookkeepingDetailEntry): string {
  return `${entry.kind}-${entry.payment_id || entry.submission_id || entry.collective_bill_uuid}`
}

function detailTitle(entry: BookkeepingDetailEntry): string {
  if (entry.kind === 'payment') {
    return `${entry.method_label || entry.method} · ${formatMoney(entry.amount_cents)}`
  }
  if (entry.collective_bill_name) {
    return `${t('events.tabs.bookkeepingOrder')} · ${entry.collective_bill_name}`
  }
  return t('events.tabs.bookkeepingOrder')
}

async function loadReport() {
  loading.value = true
  loadError.value = ''
  try {
    report.value = await apiJson<EventBookkeepingReport>(
      `/events/${props.eventId}/bookkeeping?view=both`,
    )
  } catch (e: unknown) {
    loadError.value = getErrorMessage(e, t('events.tabs.bookkeepingLoadError'))
    report.value = null
  } finally {
    loading.value = false
  }
}

onMounted(loadReport)
</script>

<style scoped>
.section-toolbar {
  margin-bottom: 1rem;
}
.sales-table-block {
  margin-top: 1.5rem;
}
.section-title {
  margin-bottom: 0.75rem;
}
.detail-block {
  margin-bottom: 1.25rem;
}
.detail-title {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
}
.warnings {
  margin-bottom: 1rem;
}
.warning {
  color: #b45309;
}
.error {
  color: #b91c1c;
}
</style>
