<template>
  <div class="event-transactions-tab">
    <div class="section-toolbar filters-toolbar">
      <v-btn variant="outlined" type="button" :disabled="loading" @click="reload">{{ $t('common.refresh') }}</v-btn>
      <v-select
        v-model="filterPaymentStatus"
        :items="paymentStatusOptions"
        item-title="label"
        item-value="value"
        :label="$t('events.tabs.status')"
        density="compact"
        hide-details
        clearable
        class="filter-field"
        @update:model-value="onFilterChange"
      />
      <v-select
        v-model="filterKind"
        :items="kindOptions"
        item-title="label"
        item-value="value"
        :label="$t('events.tabs.kind')"
        density="compact"
        hide-details
        clearable
        class="filter-field"
        @update:model-value="onFilterChange"
      />
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
      class="vq-data-table transactions-table"
      :mobile-breakpoint="TABLE_MOBILE_BREAKPOINT"
      @update:options="onOptionsUpdate"
    >
      <template #item.created_at="{ item }">{{ formatTime(item.created_at) }}</template>
      <template #item.kind="{ item }">
        <v-chip size="small" :color="kindChipColor(item.kind)" variant="tonal">
          {{ kindLabel(item.kind) }}
        </v-chip>
      </template>
      <template #item.client_order_id="{ item }">
        <span class="mono">{{ shortId(item.client_order_id) }}</span>
      </template>
      <template #item.table_number="{ item }">
        {{ item.table_number != null ? item.table_number : $t('common.emDash') }}
      </template>
      <template #item.collective_bill_name="{ item }">
        {{ item.collective_bill_name || $t('common.emDash') }}
      </template>
      <template #item.payment_status="{ item }">{{ paymentStatusLabel(item.payment_status) }}</template>
      <template #item.line_cents="{ item }">
        <div class="amount-cell">
          <span>{{ formatMoney(item.line_cents) }}</span>
          <span v-if="item.moved_line_cents" class="moved-hint muted">
            {{ formatMoney(item.moved_line_cents) }} {{ $t('events.tabs.moved') }}
          </span>
        </div>
      </template>
      <template #item.paid_cents="{ item }">
        {{ item.paid_cents ? formatMoney(item.paid_cents) : $t('common.emDash') }}
      </template>
      <template #item.line_count="{ item }">
        <span v-if="item.line_count">{{ $t('events.tabs.lineCount', { count: item.line_count }) }}</span>
        <span v-else-if="item.moved_lines?.length" class="muted">
          {{ item.moved_lines.length }} {{ $t('events.tabs.moved') }}
        </span>
        <span v-else class="muted">{{ $t('common.emDash') }}</span>
      </template>
      <template #expanded-row="{ columns, item }">
        <tr v-if="item.lines?.length || item.moved_lines?.length">
          <td :colspan="columns.length" class="expanded-cell">
            <table v-if="item.lines?.length" class="lines-nested">
              <thead>
                <tr>
                  <th>{{ $t('events.tabs.article') }}</th>
                  <th class="num">{{ $t('events.tabs.quantity') }}</th>
                  <th class="num">{{ $t('events.tabs.amount') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, idx) in item.lines" :key="`${item.id}-line-${idx}`">
                  <td>
                    <div class="name-cell">
                      <span>{{ line.name }}</span>
                      <span
                        v-for="add in line.additions || []"
                        :key="add.article_id"
                        class="addition-name"
                      >
                        + {{ add.name }}
                      </span>
                    </div>
                  </td>
                  <td class="num">{{ line.qty }}</td>
                  <td class="num">{{ formatMoney(line.line_cents) }}</td>
                </tr>
              </tbody>
            </table>
            <table v-if="item.moved_lines?.length" class="lines-nested moved-lines">
              <thead>
                <tr>
                  <th colspan="3">{{ $t('events.tabs.movedLines') }}</th>
                </tr>
                <tr>
                  <th>{{ $t('events.tabs.article') }}</th>
                  <th class="num">{{ $t('events.tabs.quantity') }}</th>
                  <th class="num">{{ $t('events.tabs.amount') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, idx) in item.moved_lines" :key="`${item.id}-moved-${idx}`">
                  <td>
                    <div class="name-cell">
                      <span>{{ line.name }}</span>
                      <span
                        v-for="add in line.additions || []"
                        :key="add.article_id"
                        class="addition-name"
                      >
                        + {{ add.name }}
                      </span>
                      <span class="transfer-note">{{ line.transfer_note }}</span>
                    </div>
                  </td>
                  <td class="num">{{ line.qty }}</td>
                  <td class="num">{{ formatMoney(line.line_cents) }}</td>
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
import { TABLE_MOBILE_BREAKPOINT } from '../constants/layout'

const { t } = useI18n()

const props = defineProps({ eventId: { type: Number, required: true } })

const headers = computed(() => [
  { title: t('events.tabs.time'), key: 'created_at', sortable: true },
  { title: t('events.tabs.kind'), key: 'kind', sortable: true },
  { title: t('events.tabs.order'), key: 'client_order_id', sortable: true },
  { title: t('events.tabs.table'), key: 'table_number', sortable: true, align: 'end' },
  { title: t('events.tabs.collectiveBill'), key: 'collective_bill_name', sortable: true },
  { title: t('events.tabs.waiter'), key: 'waiter_name', sortable: true },
  { title: t('events.tabs.status'), key: 'payment_status', sortable: true },
  { title: t('events.tabs.amount'), key: 'line_cents', sortable: true, align: 'end' },
  { title: t('events.tabs.payment'), key: 'payment_methods', sortable: false },
  { title: t('events.tabs.paid'), key: 'paid_cents', sortable: true, align: 'end' },
  { title: t('events.tabs.lineItems'), key: 'line_count', sortable: true },
])

const paymentStatusOptions = computed(() => [
  { value: 'open', label: t('events.tabs.paymentStatusOpen') },
  { value: 'paid', label: t('events.tabs.paymentStatusPaid') },
])

const kindOptions = computed(() => [
  { value: 'bestellung', label: t('events.tabs.kindOrder') },
  { value: 'teilzahlung', label: t('events.tabs.kindPartialPayment') },
  { value: 'zahlung', label: t('events.tabs.kindPayment') },
])

const loading = ref(false)
const loadError = ref('')
const currency = ref('CHF')
const items = ref([])
const totalItems = ref(0)
const page = ref(1)
const itemsPerPage = ref(25)
const sortBy = ref('created_at')
const sortDesc = ref(true)
const filterPaymentStatus = ref(null)
const filterKind = ref(null)

let optionsInitialized = false

function formatMoney(cents) {
  return `${formatAmount(cents)} ${currency.value}`
}

function formatTime(iso) {
  if (!iso) return t('common.emDash')
  try {
    return new Date(iso).toLocaleString('de-CH')
  } catch {
    return iso
  }
}

function shortId(id) {
  const s = String(id || '')
  if (s.length > 14) return `${s.slice(0, 10)}…`
  return s || t('common.emDash')
}

function kindLabel(k) {
  const map = {
    bestellung: t('events.tabs.kindOrder'),
    teilzahlung: t('events.tabs.kindPartialPayment'),
    zahlung: t('events.tabs.kindPayment'),
  }
  return map[k] || k
}

function kindChipColor(k) {
  if (k === 'zahlung') return 'success'
  if (k === 'teilzahlung') return 'info'
  return 'default'
}

function paymentStatusLabel(s) {
  const v = String(s || '').toLowerCase()
  if (v === 'paid') return t('events.tabs.paymentStatusPaid')
  if (v === 'open') return t('events.tabs.paymentStatusOpen')
  return s || t('common.emDash')
}

function buildQuery() {
  const params = new URLSearchParams()
  params.set('page', String(page.value))
  params.set('items_per_page', String(itemsPerPage.value))
  params.set('sort_by', sortBy.value)
  params.set('sort_desc', sortDesc.value ? 'true' : 'false')
  if (filterPaymentStatus.value) params.set('payment_status', filterPaymentStatus.value)
  if (filterKind.value) params.set('kind', filterKind.value)
  return params.toString()
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await apiFetch(`/events/${props.eventId}/transactions?${buildQuery()}`)
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
  const nextSortBy = sortEntry?.key ?? 'created_at'
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

function onFilterChange() {
  page.value = 1
  load()
}

function reload() {
  load()
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

.filters-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.filter-field {
  min-width: 10rem;
  max-width: 12rem;
}

.error {
  color: rgb(var(--v-theme-error));
  margin-bottom: 0.75rem;
}

.mono {
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
}

.amount-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.1rem;
}

.moved-hint {
  font-size: 0.8rem;
}

.expanded-cell {
  padding: 0.5rem 1rem 1rem !important;
  background: rgba(var(--v-theme-on-surface), 0.03);
}

.lines-nested {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.lines-nested.moved-lines {
  margin-top: 0.75rem;
}

.lines-nested th,
.lines-nested td {
  padding: 0.35rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.lines-nested th.num,
.lines-nested td.num {
  text-align: right;
  white-space: nowrap;
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

.transfer-note {
  font-size: 0.8rem;
  font-style: italic;
  opacity: 0.9;
}
</style>
