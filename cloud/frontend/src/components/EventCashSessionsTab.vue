<template>
  <div class="event-cash-sessions-tab">
    <div class="section-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="load">{{ $t('common.refresh') }}</v-btn>
    </div>
    <p v-if="loadError" class="error">{{ loadError }}</p>
    <v-data-table-server
      v-model:page="page"
      v-model:items-per-page="itemsPerPage"
      :headers="headers"
      :items="items"
      :items-length="totalItems"
      :loading="loading"
      item-value="id"
      show-expand
      class="vq-data-table"
      @update:options="onOptionsUpdate"
    >
      <template #item.subject_type="{ item }">
        {{ item.subject_type === 'cash_register'
          ? $t('events.tabs.subjectTypeCashRegister')
          : $t('events.tabs.subjectTypeWaiter') }}
      </template>
      <template #item.opening_balance_cents="{ item }">{{ formatMoney(item.opening_balance_cents) }}</template>
      <template #item.wallet_cents="{ item }">{{ formatMoney(item.wallet_cents) }}</template>
      <template #item.counted_cash_cents="{ item }">
        {{ item.counted_cash_cents != null ? formatMoney(item.counted_cash_cents) : $t('common.emDash') }}
      </template>
      <template #item.variance_cents="{ item }">
        {{ item.variance_cents != null ? formatMoney(item.variance_cents) : $t('common.emDash') }}
      </template>
      <template #expanded-row="{ columns, item }">
        <tr v-if="item.ledger?.length">
          <td :colspan="columns.length" class="expanded-cell">
            <table class="lines-nested">
              <thead>
                <tr>
                  <th>{{ $t('events.tabs.ledgerType') }}</th>
                  <th>{{ $t('events.tabs.ledgerDetails') }}</th>
                  <th class="num">{{ $t('events.tabs.amount') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in item.ledger" :key="`${item.id}-l-${idx}`">
                  <td>{{ row.entry_type }}</td>
                  <td>{{ row.method || row.voucher_name || $t('common.emDash') }}</td>
                  <td class="num">{{ formatMoney(row.amount_cents) }}</td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
      </template>
    </v-data-table-server>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiFetch } from '../api'
import { formatAmount } from '../utils/money'

const { t } = useI18n()

const props = defineProps({ eventId: { type: Number, required: true } })

const headers = computed(() => [
  { title: t('events.tabs.subjectType'), key: 'subject_type', sortable: true },
  { title: t('events.tabs.subjectName'), key: 'subject_name', sortable: true },
  { title: t('events.tabs.operatorWaiter'), key: 'operator_waiter_name', sortable: false },
  { title: t('events.tabs.status'), key: 'status', sortable: true },
  { title: t('events.tabs.openedAt'), key: 'started_at', sortable: true },
  { title: t('events.tabs.closedAtShort'), key: 'ended_at', sortable: true },
  { title: t('events.tabs.openingBalance'), key: 'opening_balance_cents', sortable: true, align: 'end' },
  { title: t('events.tabs.walletExpected'), key: 'wallet_cents', sortable: true, align: 'end' },
  { title: t('events.tabs.counted'), key: 'counted_cash_cents', sortable: true, align: 'end' },
  { title: t('events.tabs.variance'), key: 'variance_cents', sortable: true, align: 'end' },
])

const loading = ref(false)
const loadError = ref('')
const currency = ref('CHF')
const items = ref([])
const totalItems = ref(0)
const page = ref(1)
const itemsPerPage = ref(25)
const sortBy = ref('started_at')
const sortDesc = ref(true)
let optionsInitialized = false

function formatMoney(cents) {
  return `${formatAmount(cents)} ${currency.value}`
}

function buildQuery() {
  const params = new URLSearchParams()
  params.set('page', String(page.value))
  params.set('items_per_page', String(itemsPerPage.value))
  params.set('sort_by', sortBy.value)
  params.set('sort_desc', sortDesc.value ? 'true' : 'false')
  return params.toString()
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/cash-sessions?${buildQuery()}`)
    if (!resp.ok) throw new Error(await resp.text())
    const data = await resp.json()
    currency.value = data.currency || 'CHF'
    items.value = data.items || []
    totalItems.value = data.total ?? 0
  } catch (e) {
    loadError.value = e.message || t('events.tabs.loadFailed')
    items.value = []
    totalItems.value = 0
  } finally {
    loading.value = false
  }
}

function onOptionsUpdate(options) {
  const nextPage = options.page ?? 1
  const nextPerPage = options.itemsPerPage ?? 25
  const sortEntry = options.sortBy?.[0]
  const nextSortBy = sortEntry?.key ?? 'started_at'
  const nextSortDesc = sortEntry ? sortEntry.order !== 'asc' : true
  const changed =
    nextPage !== page.value ||
    nextPerPage !== itemsPerPage.value ||
    nextSortBy !== sortBy.value ||
    nextSortDesc !== sortDesc.value
  page.value = nextPage
  itemsPerPage.value = nextPerPage
  sortBy.value = nextSortBy
  sortDesc.value = nextSortDesc
  if (!optionsInitialized) {
    optionsInitialized = true
    return
  }
  if (changed) load()
}

watch(
  () => props.eventId,
  () => {
    optionsInitialized = false
    page.value = 1
    load()
  },
  { immediate: true },
)
</script>

<style scoped>
.section-toolbar {
  margin-bottom: 1rem;
}
.error {
  color: rgb(var(--v-theme-error));
}
.expanded-cell {
  padding: 0.5rem 1rem 1rem !important;
}
.lines-nested {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.lines-nested th.num,
.lines-nested td.num {
  text-align: right;
}
</style>
