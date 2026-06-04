<template>
  <ListDetailLayout
    title="Veranstaltungen"
    subtitle="Events verwalten und nach Organisation sichtbar machen."
    createLabel="Neue Veranstaltung"
    :showCreate="canCreateEvents"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? 'Veranstaltung bearbeiten' : 'Neue Veranstaltung' }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> Pflichtfeld</p>

      <EventConfiguration
        v-if="editMode && activeId"
        :event-id="activeId"
        :organisation-id="activeOrganisationId"
        :event-status="form.status"
        :cash-registers-enabled="form.cashRegistersEnabled"
        :vouchers-enabled="form.vouchersEnabled"
        :shift-settlement-enabled="form.shiftSettlementEnabled"
        :stammdaten-dirty="stammdatenDirty"
      >
        <template #stammdaten>
          <v-form ref="stammdatenFormRef" @submit.prevent="saveEvent">
            <EventStammdatenFields
              :form="form"
              :selectable-status-options="selectableStatusOptions"
              :currency-options="currencyOptions"
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
              <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
              <v-btn variant="outlined" type="button" :disabled="copyBusy" @click="copyEvent">
                Event kopieren
              </v-btn>
              <v-btn color="primary" type="submit">Speichern</v-btn>
            </div>
            <p v-if="message" :class="messageType">{{ message }}</p>
          </v-form>
        </template>
      </EventConfiguration>

      <v-form v-else ref="stammdatenFormRef" @submit.prevent="saveEvent">
        <EventStammdatenFields
          :form="form"
          :selectable-status-options="selectableStatusOptions"
          :currency-options="currencyOptions"
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
          <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
          <v-btn color="primary" type="submit">Speichern</v-btn>
        </div>
        <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        Bitte wählen Sie links eine Organisation.
      </p>
      <div class="table-header">
        <h2>Alle Veranstaltungen</h2>
        <span>{{ filteredEvents.length }} von {{ eventsInActiveOrganisation.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            label="Suche"
            prepend-inner-icon="mdi-magnify"
            placeholder="Name, Organisation oder Währung suchen..."
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
            label="Status"
            hide-details
            density="compact"
          />
        </div>
      </div>

      <VqDataTable
        :headers="tableHeaders"
        :items="paginatedEvents"
        item-value="id"
        class="vq-data-table list-table"
        hide-default-footer
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
            Löschen
          </v-btn>
        </template>
        <template #no-data>Keine Veranstaltungen gefunden.</template>
      </VqDataTable>

      <div v-if="filteredEvents.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" density="compact" />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import ListDetailLayout from './ListDetailLayout.vue'
import EventConfiguration from './EventConfiguration.vue'
import EventStammdatenFields from './EventStammdatenFields.vue'
import { apiFetch } from '../api'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { matchesActiveOrganisation } from '../utils/orgScope'
import { validateForm } from '../utils/formRules.js'
import VqDataTable from './VqDataTable.vue'

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
const currentPage = ref(1)
const pageSize = 20

const statusOptions = [
  { value: 'config', label: 'Konfiguration' },
  { value: 'test', label: 'Testbetrieb' },
  { value: 'prod', label: 'Produktivbetrieb' },
  { value: 'archive', label: 'Archiviert' },
]
const statusFilterOptions = [{ value: '', label: 'Alle Status' }, ...statusOptions]
const currencyOptions = ['EUR', 'CHF', 'USD', 'GBP']
const paymentModeOptions = [
  { value: 'instant', label: 'Sofort bezahlt' },
  { value: 'pay_now', label: 'Jetzt bezahlen' },
  { value: 'pay_later', label: 'Später bezahlen' },
]
const paymentTypeOptions = [
  { value: 'cash', label: 'Bargeld' },
  { value: 'twint', label: 'TWINT' },
  { value: 'sumup', label: 'SumUp' },
  { value: 'stripe_terminal', label: 'Karte (Stripe Terminal)' },
]

const emptyForm = () => ({
  name: '',
  status: 'config',
  start: null,
  end: null,
  currency: 'EUR',
  paymentMode: 'pay_later',
  paymentTypes: ['cash'],
  cashRegistersEnabled: false,
  shiftSettlementEnabled: false,
  vouchersEnabled: false,
  discountsEnabled: false,
  offerPaymentReceipt: false,
})

const form = ref(emptyForm())
const stammdatenFormRef = ref(null)
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
    currency: form.value.currency,
    paymentMode: form.value.paymentMode,
    paymentTypes: types,
    cashRegistersEnabled: Boolean(form.value.cashRegistersEnabled),
    shiftSettlementEnabled: Boolean(form.value.shiftSettlementEnabled),
    vouchersEnabled: Boolean(form.value.vouchersEnabled),
    discountsEnabled: Boolean(form.value.discountsEnabled),
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
    return statusOptions.filter((o) => o.value === 'config')
  }
  const cur = originalStatus.value || form.value.status || 'config'
  const allowed = new Set([cur])
  const next = { config: ['test'], test: ['prod'], prod: ['archive'], archive: [] }[cur] || []
  for (const s of next) allowed.add(s)
  return statusOptions.filter((o) => allowed.has(o.value))
})

function statusLabel(status) {
  return statusOptions.find((item) => item.value === status)?.label || status
}

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
    { title: 'ID', key: 'id' },
    { title: 'Name', key: 'name' },
    { title: 'Status', key: 'status', sortable: false },
    { title: 'Organisation', key: 'organisation_name' },
    { title: 'Start', key: 'start', sortable: false },
    { title: 'Ende', key: 'end', sortable: false },
    { title: 'Währung', key: 'currency' },
  ]
  if (props.isAdmin) {
    headers.push({ title: 'Aktionen', key: 'actions', sortable: false, align: 'end' })
  }
  return headers
})

function formatDateTime(value) {
  if (!value) return '—'
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
    event.currency,
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

const totalPages = computed(() => Math.max(1, Math.ceil(filteredEvents.value.length / pageSize)))

const paginatedEvents = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredEvents.value.slice(start, start + pageSize)
})

const paginationLabel = computed(() => {
  if (!filteredEvents.value.length) return '0 Einträge'
  const start = (currentPage.value - 1) * pageSize + 1
  const end = Math.min(currentPage.value * pageSize, filteredEvents.value.length)
  return `${start}-${end} von ${filteredEvents.value.length}`
})

watch([searchQuery, statusFilter, () => props.activeOrganisationId], () => {
  currentPage.value = 1
})

watch(
  () => props.activeOrganisationId,
  () => {
    if (showDetail.value) goToList()
  },
)

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

async function fetchEvents() {
  try {
    const response = await apiFetch('/events/')
    if (!response.ok) throw new Error(await response.text())
    events.value = await response.json()
  } catch (error) {
    message.value = 'Veranstaltungen konnten nicht geladen werden.'
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
    message.value = 'TWINT QR-Code gespeichert.'
    messageType.value = 'success'
  } catch {
    message.value = 'TWINT QR-Code konnte nicht hochgeladen werden.'
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
    message.value = 'TWINT QR-Code entfernt.'
    messageType.value = 'success'
  } catch {
    message.value = 'TWINT QR-Code konnte nicht entfernt werden.'
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
    currency: event.currency || 'EUR',
    paymentMode: event.payment_mode || 'pay_later',
    paymentTypes: Array.isArray(event.payment_types) && event.payment_types.length
      ? [...event.payment_types]
      : ['cash'],
    cashRegistersEnabled: Boolean(event.cash_registers_enabled),
    shiftSettlementEnabled: Boolean(event.shift_settlement_enabled),
    vouchersEnabled: Boolean(event.vouchers_enabled),
    discountsEnabled: Boolean(event.discounts_enabled),
    offerPaymentReceipt: Boolean(event.offer_payment_receipt),
  }
  originalStatus.value = event.status || 'config'
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
      message.value = 'Veranstaltung nicht gefunden.'
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
  const base = (name || '').trim() || 'Event'
  const suffix = ' (Kopie)'
  return base.endsWith(suffix) ? base : `${base}${suffix}`
}

async function copyEvent() {
  if (!activeId.value) return
  if (!(await validateForm(stammdatenFormRef))) return
  const suggested = defaultCopyName(form.value.name)
  const entered = window.prompt('Name der kopierten Veranstaltung', suggested)
  if (entered === null) return
  const name = entered.trim()
  if (!name) {
    message.value = 'Name ist erforderlich.'
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
    message.value = `Veranstaltung «${created.name}» erstellt.`
    messageType.value = 'success'
    await goToDetail(created.id)
    await applyEventToForm(created)
  } catch {
    message.value = 'Event konnte nicht kopiert werden.'
    messageType.value = 'error'
  } finally {
    copyBusy.value = false
  }
}

async function saveEvent() {
  if (props.activeOrganisationId == null) {
    message.value = 'Bitte wählen Sie links eine Organisation.'
    messageType.value = 'error'
    return
  }
  if (!(await validateForm(stammdatenFormRef))) return
  if (
    editMode.value &&
    originalStatus.value === 'test' &&
    form.value.status === 'prod' &&
    !confirm(
      'Wechsel zu Produktivbetrieb: Alle Testbestellungen auf dem Pi, Statistiken in der Cloud und Bestandsänderungen aus dem Testbetrieb werden gelöscht bzw. zurückgesetzt. Fortfahren?'
    )
  ) {
    return
  }

  const payload = {
    name: form.value.name,
    status: form.value.status,
    start: toIso(form.value.start),
    end: toIso(form.value.end),
    currency: form.value.currency,
    payment_mode: form.value.paymentMode,
    payment_types: form.value.paymentTypes,
    cash_registers_enabled: Boolean(form.value.cashRegistersEnabled),
    shift_settlement_enabled: Boolean(form.value.shiftSettlementEnabled),
    vouchers_enabled: Boolean(form.value.vouchersEnabled),
    discounts_enabled: Boolean(form.value.discountsEnabled),
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
    }
    await fetchEvents()
    message.value = wasEdit ? 'Veranstaltung aktualisiert.' : 'Veranstaltung erstellt.'
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = 'Fehler beim Speichern der Veranstaltung.'
    messageType.value = 'error'
  }
}

async function deleteEvent(id) {
  if (!confirm('Veranstaltung wirklich löschen?')) return
  try {
    const response = await apiFetch(`/events/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error(await response.text())
    await fetchEvents()
    message.value = 'Veranstaltung gelöscht.'
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = 'Veranstaltung konnte nicht gelöscht werden.'
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

h2 {
  margin: 0 0 1.5rem;
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

.table-header span,
.pagination {
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

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
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

@media (max-width: 700px) {
  .pagination {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
