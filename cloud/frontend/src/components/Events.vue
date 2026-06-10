<template>
  <ListDetailLayout
    :title="t('events.title')"
    :subtitle="t('events.subtitle')"
    :createLabel="t('events.createLabel')"
    :showCreate="canCreateEvents"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <div class="detail-header-row">
        <h2>{{ editMode ? t('events.editTitle') : t('events.createTitle') }}</h2>
        <HelpLink v-if="editMode" slug="event-setup" variant="icon" />
      </div>
      <p v-if="!editMode" class="form-required-legend"><span class="vq-asterisk">*</span> {{ t('common.requiredLegend') }}</p>

      <EventConfiguration
        v-if="editMode && activeId"
        ref="eventConfigurationRef"
        :event-id="activeId"
        :organisation-id="activeOrganisationId"
        :organisation-currency="organisationCurrency"
        :event-status="form.status"
        :cash-registers-enabled="form.cashRegistersEnabled"
        :vouchers-enabled="form.vouchersEnabled"
        :shift-settlement-enabled="form.shiftSettlementEnabled"
        :alternative-printers-enabled="form.alternativePrintersEnabled"
        :kitchen-monitors-enabled="form.kitchenMonitorsEnabled"
        :stammdaten-dirty="stammdatenDirty"
      >
        <template #stammdaten>
          <HostedPiCard v-if="form.status === 'config'" :event-id="activeId" />
          <v-form ref="stammdatenFormRef" @submit.prevent="saveEvent">
            <EventStammdatenFields
              :form="form"
              :selectable-status-options="selectableStatusOptions"
              :payment-mode-options="paymentModeOptions"
              :payment-type-options="paymentTypeOptions"
              :show-twint-qr-section="showTwintQrSection"
              :edit-mode="editMode"
              :active-id="activeId"
              :has-twint-qr="hasTwintQr"
              :twint-qr-preview-url="twintQrPreviewUrl"
              :twint-qr-busy="twintQrBusy"
              @upload="uploadTwintQr"
              @remove="removeTwintQr"
            />
            <div class="actions">
              <v-btn variant="outlined" type="button" @click="resetForm">{{ t('appliances.back') }}</v-btn>
              <v-btn variant="outlined" type="button" :disabled="copyBusy" @click="copyEvent">
                {{ t('events.copyEvent') }}
              </v-btn>
              <v-btn color="primary" type="submit">{{ t('common.save') }}</v-btn>
            </div>
            <p v-if="message" :class="messageType">{{ message }}</p>
          </v-form>
        </template>
      </EventConfiguration>

      <v-form v-else ref="stammdatenFormRef" @submit.prevent="saveEvent">
        <EventStammdatenFields
          :form="form"
          :selectable-status-options="selectableStatusOptions"
          :payment-mode-options="paymentModeOptions"
          :payment-type-options="paymentTypeOptions"
          :show-twint-qr-section="showTwintQrSection"
          :edit-mode="editMode"
          :active-id="activeId"
          :has-twint-qr="hasTwintQr"
          :twint-qr-preview-url="twintQrPreviewUrl"
          :twint-qr-busy="twintQrBusy"
          @upload="uploadTwintQr"
          @remove="removeTwintQr"
        />
        <div class="actions">
          <v-btn variant="outlined" type="button" @click="resetForm">{{ t('appliances.back') }}</v-btn>
          <v-btn color="primary" type="submit">{{ t('common.save') }}</v-btn>
        </div>
        <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        {{ t('common.noOrganisation') }}
      </p>
      <div class="table-header">
        <h2>{{ t('events.allEvents') }}</h2>
        <span>{{ t('events.entryCount', { filtered: filteredEvents.length, total: eventsInActiveOrganisation.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            :label="t('common.search')"
            prepend-inner-icon="mdi-magnify"
            :placeholder="t('events.searchPlaceholder')"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="statusFilter"
            :items="statusFilterOptions"
            item-title="label"
            item-value="value"
            :label="t('events.table.status')"
            hide-details
            density="compact"
          />
        </div>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredEvents"
        :items-per-page="pageSize"
        item-value="id"
        class="vq-data-table list-table"
        hover
        @click:row="(_, { item }) => editEvent(item)"
      >
        <template #item.status="{ item }">
          <v-chip :color="statusChipColor(item.status)" size="small" variant="tonal">
            {{ statusLabel(item.status) }}
          </v-chip>
        </template>
        <template #item.start="{ item }">{{ formatDateTime(item.start) }}</template>
        <template #item.end="{ item }">{{ formatDateTime(item.end) }}</template>
        <template v-if="isAdmin" #item.actions="{ item }">
          <v-btn color="error" variant="outlined" size="small" @click.stop="deleteEvent(item.id)">
            {{ t('common.delete') }}
          </v-btn>
        </template>
        <template #no-data>{{ t('events.noResults') }}</template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ListDetailLayout from './ListDetailLayout.vue'
import HelpLink from './HelpLink.vue'
import EventConfiguration from './EventConfiguration.vue'
import EventStammdatenFields from './EventStammdatenFields.vue'
import HostedPiCard from './HostedPiCard.vue'
import { apiFetch } from '../api'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { matchesActiveOrganisation } from '../utils/orgScope'
import { validateForm } from '../utils/formRules.js'
import { statusLabel } from '../utils/dashboardMetrics'
import VqDataTable from './VqDataTable.vue'

const { t } = useI18n()

const props = defineProps({
  isAdmin: {
    type: Boolean,
    default: false,
  },
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('events')

const events = ref([])
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const statusFilter = ref('')

const STATUS_VALUES = ['config', 'test', 'prod', 'archive']
const PAYMENT_MODE_VALUES = ['instant', 'pay_now', 'pay_later']
const PAYMENT_TYPE_VALUES = ['cash', 'twint', 'sumup', 'stripe_terminal']

const statusOptions = computed(() =>
  STATUS_VALUES.map((value) => ({ value, label: t(`eventStatus.${value}`) })),
)
const statusFilterOptions = computed(() => [
  { value: '', label: t('events.allStatus') },
  ...statusOptions.value,
])
const paymentModeOptions = computed(() =>
  PAYMENT_MODE_VALUES.map((value) => ({ value, label: t(`events.paymentMode.${value}`) })),
)
const paymentTypeOptions = computed(() =>
  PAYMENT_TYPE_VALUES.map((value) => ({ value, label: t(`events.paymentType.${value}`) })),
)

const organisationCurrency = ref('EUR')

const emptyForm = () => ({
  name: '',
  status: 'config',
  start: null,
  end: null,
  paymentMode: 'pay_later',
  paymentTypes: ['cash'],
  cashRegistersEnabled: false,
  shiftSettlementEnabled: false,
  vouchersEnabled: false,
  discountsEnabled: false,
  alternativePrintersEnabled: false,
  kitchenMonitorsEnabled: false,
  offerPaymentReceipt: false,
})

const form = ref(emptyForm())
const stammdatenFormRef = ref(null)
const eventConfigurationRef = ref(null)
const stammdatenBaseline = ref('')
const originalStatus = ref('config')

function stammdatenSnapshot() {
  const types = Array.isArray(form.value.paymentTypes) ? [...form.value.paymentTypes] : []
  types.sort()
  return JSON.stringify({
    name: (form.value.name || '').trim(),
    status: form.value.status,
    start: toIso(form.value.start),
    end: toIso(form.value.end),
    paymentMode: form.value.paymentMode,
    paymentTypes: types,
    cashRegistersEnabled: Boolean(form.value.cashRegistersEnabled),
    shiftSettlementEnabled: Boolean(form.value.shiftSettlementEnabled),
    vouchersEnabled: Boolean(form.value.vouchersEnabled),
    discountsEnabled: Boolean(form.value.discountsEnabled),
    alternativePrintersEnabled: Boolean(form.value.alternativePrintersEnabled),
    kitchenMonitorsEnabled: Boolean(form.value.kitchenMonitorsEnabled),
    offerPaymentReceipt: Boolean(form.value.offerPaymentReceipt),
  })
}

const stammdatenDirty = computed(() => {
  if (!editMode.value || !stammdatenBaseline.value) return false
  return stammdatenSnapshot() !== stammdatenBaseline.value
})
const hasTwintQr = ref(false)
const twintQrPreviewUrl = ref('')
const twintQrBusy = ref(false)
const copyBusy = ref(false)

const showTwintQrSection = computed(() =>
  Array.isArray(form.value.paymentTypes) && form.value.paymentTypes.includes('twint')
)

const canCreateEvents = computed(() => props.activeOrganisationId != null)

const selectableStatusOptions = computed(() => {
  if (!editMode.value) {
    return statusOptions.value.filter((o) => o.value === 'config')
  }
  const cur = originalStatus.value || form.value.status || 'config'
  const allowed = new Set([cur])
  const next = { config: ['test'], test: ['prod'], prod: ['archive'], archive: [] }[cur] || []
  for (const s of next) allowed.add(s)
  return statusOptions.value.filter((o) => allowed.has(o.value))
})

function statusChipColor(status) {
  return {
    config: undefined,
    test: 'info',
    prod: 'success',
    archive: 'warning',
  }[status]
}

const tableHeaders = computed(() => {
  const headers = [
    { title: t('events.table.id'), key: 'id' },
    { title: t('events.table.name'), key: 'name' },
    { title: t('events.table.status'), key: 'status', sortable: false },
    { title: t('events.table.organisation'), key: 'organisation_name' },
    { title: t('events.table.start'), key: 'start', sortable: false },
    { title: t('events.table.end'), key: 'end', sortable: false },
  ]
  if (props.isAdmin) {
    headers.push({ title: t('events.table.actions'), key: 'actions', sortable: false, align: 'end' })
  }
  return headers
})

function formatDateTime(value) {
  if (!value) return t('common.emDash')
  return new Intl.DateTimeFormat('de-DE', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function parseDate(value) {
  return value ? new Date(value) : null
}

function toIso(value) {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString()
}

function matchesSearch(event, term) {
  if (!term) return true
  return [
    event.id,
    event.name,
    event.status,
    statusLabel(event.status),
    event.organisation_name,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredEvents = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return events.value.filter((event) => {
    if (!matchesSearch(event, term)) return false
    if (statusFilter.value && event.status !== statusFilter.value) return false
    if (!matchesActiveOrganisation(props.activeOrganisationId, event.organisation_id)) return false
    return true
  })
})

const eventsInActiveOrganisation = computed(() =>
  events.value.filter((event) =>
    matchesActiveOrganisation(props.activeOrganisationId, event.organisation_id)
  )
)

const { currentPage, pageSize } = useClientPagination(filteredEvents, {
  resetOn: [searchQuery, statusFilter, () => props.activeOrganisationId],
})

watch(
  () => props.activeOrganisationId,
  () => {
    if (showDetail.value) goToList()
  },
)

async function fetchEvents() {
  try {
    const response = await apiFetch('/events/')
    if (!response.ok) throw new Error(await response.text())
    events.value = await response.json()
  } catch (error) {
    message.value = t('events.messages.loadFailed')
    messageType.value = 'error'
  }
}

function revokeTwintQrPreview() {
  if (twintQrPreviewUrl.value) {
    URL.revokeObjectURL(twintQrPreviewUrl.value)
    twintQrPreviewUrl.value = ''
  }
}

async function loadTwintQrPreview() {
  revokeTwintQrPreview()
  if (!activeId.value || !hasTwintQr.value) return
  try {
    const response = await apiFetch(`/events/${activeId.value}/twint-qr`)
    if (!response.ok) return
    const blob = await response.blob()
    twintQrPreviewUrl.value = URL.createObjectURL(blob)
  } catch {
    /* preview optional */
  }
}

async function uploadTwintQr(file) {
  if (!activeId.value || !file) return
  twintQrBusy.value = true
  try {
    const body = new FormData()
    body.append('file', file)
    const response = await apiFetch(`/events/${activeId.value}/twint-qr`, {
      method: 'PUT',
      body,
    })
    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || 'Upload failed')
    }
    hasTwintQr.value = true
    await loadTwintQrPreview()
    const idx = events.value.findIndex((e) => e.id === activeId.value)
    if (idx >= 0) events.value[idx] = { ...events.value[idx], has_twint_qr: true }
    message.value = t('events.messages.twintQrSaved')
    messageType.value = 'success'
  } catch {
    message.value = t('events.messages.twintQrUploadFailed')
    messageType.value = 'error'
  } finally {
    twintQrBusy.value = false
  }
}

async function removeTwintQr() {
  if (!activeId.value) return
  twintQrBusy.value = true
  try {
    const response = await apiFetch(`/events/${activeId.value}/twint-qr`, { method: 'DELETE' })
    if (!response.ok && response.status !== 204) throw new Error('delete failed')
    hasTwintQr.value = false
    revokeTwintQrPreview()
    const idx = events.value.findIndex((e) => e.id === activeId.value)
    if (idx >= 0) events.value[idx] = { ...events.value[idx], has_twint_qr: false }
    message.value = t('events.messages.twintQrRemoved')
    messageType.value = 'success'
  } catch {
    message.value = t('events.messages.twintQrRemoveFailed')
    messageType.value = 'error'
  } finally {
    twintQrBusy.value = false
  }
}

function clearFormState() {
  hasTwintQr.value = false
  revokeTwintQrPreview()
  form.value = emptyForm()
  originalStatus.value = 'config'
  stammdatenBaseline.value = ''
  message.value = ''
}

async function applyEventToForm(event) {
  hasTwintQr.value = Boolean(event.has_twint_qr)
  revokeTwintQrPreview()
  form.value = {
    name: event.name || '',
    status: event.status || 'config',
    start: parseDate(event.start),
    end: parseDate(event.end),
    paymentMode: event.payment_mode || 'pay_later',
    paymentTypes: Array.isArray(event.payment_types) && event.payment_types.length
      ? [...event.payment_types]
      : ['cash'],
    cashRegistersEnabled: Boolean(event.cash_registers_enabled),
    shiftSettlementEnabled: Boolean(event.shift_settlement_enabled),
    vouchersEnabled: Boolean(event.vouchers_enabled),
    discountsEnabled: Boolean(event.discounts_enabled),
    alternativePrintersEnabled: Boolean(event.alternative_printers_enabled),
    kitchenMonitorsEnabled: Boolean(event.kitchen_monitors_enabled),
    offerPaymentReceipt: Boolean(event.offer_payment_receipt),
  }
  originalStatus.value = event.status || 'config'
  organisationCurrency.value = event.organisation_currency || 'EUR'
  stammdatenBaseline.value = stammdatenSnapshot()
  message.value = ''
  if (hasTwintQr.value) await loadTwintQrPreview()
}

async function syncRouteToForm() {
  if (!showDetail.value) {
    clearFormState()
    return
  }
  if (isCreateMode.value) {
    clearFormState()
    return
  }
  const id = routeEntityId.value
  if (id == null) {
    goToList()
    return
  }
  let row = events.value.find((e) => Number(e.id) === Number(id))
  if (!row) {
    try {
      const response = await apiFetch(`/events/${id}`)
      if (!response.ok) throw new Error(await response.text())
      row = await response.json()
    } catch {
      message.value = t('events.messages.notFound')
      messageType.value = 'error'
      goToList()
      return
    }
  }
  await applyEventToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

async function editEvent(event) {
  await applyEventToForm(event)
  goToDetail(event.id)
}

function defaultCopyName(name) {
  const base = (name || '').trim() || t('events.copy.defaultName')
  const suffix = t('events.copy.defaultSuffix')
  return base.endsWith(suffix) ? base : `${base}${suffix}`
}

async function copyEvent() {
  if (!activeId.value) return
  if (!(await validateForm(stammdatenFormRef))) return
  const suggested = defaultCopyName(form.value.name)
  const entered = window.prompt(t('events.copy.prompt'), suggested)
  if (entered === null) return
  const name = entered.trim()
  if (!name) {
    message.value = t('events.copy.nameRequired')
    messageType.value = 'error'
    return
  }
  copyBusy.value = true
  try {
    const response = await apiFetch(`/events/${activeId.value}/copy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    if (!response.ok) throw new Error(await response.text())
    const created = await response.json()
    await fetchEvents()
    message.value = t('events.copy.created', { name: created.name })
    messageType.value = 'success'
    await goToDetail(created.id)
    await applyEventToForm(created)
  } catch {
    message.value = t('events.copy.failed')
    messageType.value = 'error'
  } finally {
    copyBusy.value = false
  }
}

async function saveEvent() {
  if (props.activeOrganisationId == null) {
    message.value = t('common.noOrganisation')
    messageType.value = 'error'
    return
  }
  if (!(await validateForm(stammdatenFormRef))) return
  if (
    editMode.value &&
    originalStatus.value === 'test' &&
    form.value.status === 'prod' &&
    !confirm(t('events.confirmProd'))
  ) {
    return
  }

  const payload = {
    name: form.value.name,
    status: form.value.status,
    start: toIso(form.value.start),
    end: toIso(form.value.end),
    payment_mode: form.value.paymentMode,
    payment_types: form.value.paymentTypes,
    cash_registers_enabled: Boolean(form.value.cashRegistersEnabled),
    shift_settlement_enabled: Boolean(form.value.shiftSettlementEnabled),
    vouchers_enabled: Boolean(form.value.vouchersEnabled),
    discounts_enabled: Boolean(form.value.discountsEnabled),
    alternative_printers_enabled: Boolean(form.value.alternativePrintersEnabled),
    kitchen_monitors_enabled: Boolean(form.value.kitchenMonitorsEnabled),
    offer_payment_receipt: Boolean(form.value.offerPaymentReceipt),
  }
  if (!editMode.value) {
    payload.organisation_id = props.activeOrganisationId
  }

  try {
    const path = editMode.value ? `/events/${activeId.value}` : '/events/'
    const method = editMode.value ? 'PUT' : 'POST'
    const response = await apiFetch(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    if (!response.ok) throw new Error(await response.text())
    const wasEdit = editMode.value
    if (wasEdit) {
      stammdatenBaseline.value = stammdatenSnapshot()
      await eventConfigurationRef.value?.loadConfiguration?.()
    }
    await fetchEvents()
    message.value = wasEdit ? t('events.messages.updated') : t('events.messages.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('events.messages.saveFailed')
    messageType.value = 'error'
  }
}

async function deleteEvent(id) {
  if (!confirm(t('events.confirmDelete'))) return
  try {
    const response = await apiFetch(`/events/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error(await response.text())
    await fetchEvents()
    message.value = t('events.messages.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('events.messages.deleteFailed')
    messageType.value = 'error'
  }
}

onMounted(fetchEvents)

onUnmounted(() => {
  revokeTwintQrPreview()
})
</script>

<style scoped>
.empty-hint {
  color: rgba(var(--v-theme-on-surface), 0.65);
  margin: 0 0 1rem;
}

.detail-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.detail-header-row h2 {
  margin: 0;
  color: rgb(var(--v-theme-on-surface));
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.table-header h2 {
  margin: 0;
}

.table-header span {
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 0.9rem;
}

.list-controls {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 180px;
  gap: 1rem;
  margin-bottom: 1rem;
}

.search-field,
.filter-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.list-table {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}

.success,
.error {
  margin-top: 1rem;
}

@media (max-width: 1000px) {
  .list-controls {
    grid-template-columns: 1fr;
  }
}
</style>
