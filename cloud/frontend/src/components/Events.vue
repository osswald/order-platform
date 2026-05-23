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

      <EventConfiguration
        v-if="editMode && activeId"
        :event-id="activeId"
        :organisation-id="form.organisationId"
      >
        <template #stammdaten>
          <div class="event-stammdaten">
            <div class="form-field">
              <label>Name</label>
              <InputText v-model="form.name" placeholder="Sommerfest 2026" />
            </div>

            <div class="field-row">
              <div class="form-field">
                <label>Status</label>
                <Select v-model="form.status" :options="selectableStatusOptions" optionLabel="label" optionValue="value" placeholder="Status wählen" />
              </div>
              <div class="form-field">
                <label>Währung</label>
                <Select v-model="form.currency" :options="currencyOptions" placeholder="Währung wählen" />
              </div>
            </div>

            <div class="field-row">
              <div class="form-field">
                <label>Start</label>
                <DatePicker v-model="form.start" showIcon showTime hourFormat="24" dateFormat="dd.mm.yy" placeholder="Startdatum wählen" />
              </div>
              <div class="form-field">
                <label>Ende</label>
                <DatePicker v-model="form.end" showIcon showTime hourFormat="24" dateFormat="dd.mm.yy" placeholder="Enddatum wählen" />
              </div>
            </div>

            <div class="form-field">
              <label>Zahlungsmodus (Pi / Kellner)</label>
              <Select
                v-model="form.paymentMode"
                :options="paymentModeOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Modus wählen"
              />
              <small>Sofort bezahlt = Position als bezahlt beim Absenden; Jetzt bezahlen = vor Abschluss; Später = nach Absenden.</small>
            </div>

            <div class="form-field">
              <label>Zahlungsarten (Pi)</label>
              <MultiSelect
                v-model="form.paymentTypes"
                :options="paymentTypeOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Zahlungsarten wählen"
                display="chip"
                class="w-full"
              />
              <small>Bei Abrechnung wählt der Kellner eine Art (Popup nur bei mehreren).</small>
            </div>

            <TwintQrField
              v-if="showTwintQrSection"
              :edit-mode="editMode"
              :active-id="activeId"
              :has-twint-qr="hasTwintQr"
              :preview-url="twintQrPreviewUrl"
              :busy="twintQrBusy"
              @upload="uploadTwintQr"
              @remove="removeTwintQr"
            />

            <div class="form-field">
              <label>Organisation</label>
              <Select
                v-model="form.organisationId"
                :options="organisationOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Organisation wählen"
                :disabled="organisationOptions.length === 1"
                filter
              />
              <small>Nur Benutzer dieser Organisation können die Veranstaltung sehen. Administratoren sehen alle.</small>
            </div>

            <div class="actions">
              <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
              <Button
                label="Event kopieren"
                class="secondary-button"
                type="button"
                :disabled="copyBusy"
                @click="copyEvent"
              />
              <Button
                label="Speichern"
                class="primary-button"
                :disabled="!canSave"
                @click="saveEvent"
              />
            </div>
            <p v-if="message" :class="messageType">{{ message }}</p>
          </div>
        </template>
      </EventConfiguration>

      <template v-else>
        <div class="form-field">
          <label>Name</label>
          <InputText v-model="form.name" placeholder="Sommerfest 2026" />
        </div>

        <div class="field-row">
          <div class="form-field">
            <label>Status</label>
            <Select v-model="form.status" :options="selectableStatusOptions" optionLabel="label" optionValue="value" placeholder="Status wählen" />
          </div>
          <div class="form-field">
            <label>Währung</label>
            <Select v-model="form.currency" :options="currencyOptions" placeholder="Währung wählen" />
          </div>
        </div>

        <div class="field-row">
          <div class="form-field">
            <label>Start</label>
            <DatePicker v-model="form.start" showIcon showTime hourFormat="24" dateFormat="dd.mm.yy" placeholder="Startdatum wählen" />
          </div>
          <div class="form-field">
            <label>Ende</label>
            <DatePicker v-model="form.end" showIcon showTime hourFormat="24" dateFormat="dd.mm.yy" placeholder="Enddatum wählen" />
          </div>
        </div>

        <div class="form-field">
          <label>Zahlungsmodus (Pi / Kellner)</label>
          <Select
            v-model="form.paymentMode"
            :options="paymentModeOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Modus wählen"
          />
          <small>Sofort bezahlt = Position als bezahlt beim Absenden; Jetzt bezahlen = vor Abschluss; Später = nach Absenden.</small>
        </div>

        <div class="form-field">
          <label>Zahlungsarten (Pi)</label>
          <MultiSelect
            v-model="form.paymentTypes"
            :options="paymentTypeOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Zahlungsarten wählen"
            display="chip"
            class="w-full"
          />
          <small>Bei Abrechnung wählt der Kellner eine Art (Popup nur bei mehreren).</small>
        </div>

        <TwintQrField
          v-if="showTwintQrSection"
          :edit-mode="editMode"
          :active-id="activeId"
          :has-twint-qr="hasTwintQr"
          :preview-url="twintQrPreviewUrl"
          :busy="twintQrBusy"
          @upload="uploadTwintQr"
          @remove="removeTwintQr"
        />

        <div class="form-field">
          <label>Organisation</label>
          <Select
            v-model="form.organisationId"
            :options="organisationOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Organisation wählen"
            :disabled="organisationOptions.length === 1"
            filter
          />
          <small>Nur Benutzer dieser Organisation können die Veranstaltung sehen. Administratoren sehen alle.</small>
        </div>

        <div class="actions">
          <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
          <Button
            label="Speichern"
            class="primary-button"
            :disabled="!canSave"
            @click="saveEvent"
          />
        </div>
        <p v-if="message" :class="messageType">{{ message }}</p>
      </template>
    </template>

    <template #table>
      <div class="table-header">
        <h2>Alle Veranstaltungen</h2>
        <span>{{ filteredEvents.length }} von {{ eventsInActiveOrganisation.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="searchQuery" placeholder="Name, Organisation oder Währung suchen..." />
          </IconField>
        </div>
        <div class="filter-field">
          <label>Status</label>
          <Select v-model="statusFilter" :options="statusFilterOptions" optionLabel="label" optionValue="value" placeholder="Alle Status" />
        </div>
      </div>

      <DataTable
        :value="paginatedEvents"
        dataKey="id"
        responsiveLayout="scroll"
        class="list-table"
        @row-click="editEvent($event.data)"
      >
        <template #empty>Keine Veranstaltungen gefunden.</template>
        <Column field="id" header="ID" />
        <Column field="name" header="Name" />
        <Column header="Status">
          <template #body="{ data }">
            <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" />
          </template>
        </Column>
        <Column field="organisation_name" header="Organisation" />
        <Column header="Start">
          <template #body="{ data }">{{ formatDateTime(data.start) }}</template>
        </Column>
        <Column header="Ende">
          <template #body="{ data }">{{ formatDateTime(data.end) }}</template>
        </Column>
        <Column field="currency" header="Währung" />
        <Column v-if="isAdmin" header="Aktionen">
          <template #body="{ data }">
            <Button label="Löschen" class="danger" @click.stop="deleteEvent(data.id)" />
          </template>
        </Column>
      </DataTable>

      <div v-if="filteredEvents.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <Paginator
          :first="(currentPage - 1) * pageSize"
          :rows="pageSize"
          :totalRecords="filteredEvents.length"
          @page="currentPage = $event.page + 1"
        />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ListDetailLayout from './ListDetailLayout.vue'
import EventConfiguration from './EventConfiguration.vue'
import TwintQrField from './TwintQrField.vue'
import { apiFetch } from '../api'
import { matchesActiveOrganisation } from '../orgScope'

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

const events = ref([])
const organisations = ref([])
const showDetail = ref(false)
const editMode = ref(false)
const activeId = ref(null)
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
]

const emptyForm = () => ({
  name: '',
  status: 'config',
  start: null,
  end: null,
  currency: 'EUR',
  paymentMode: 'pay_later',
  paymentTypes: ['cash'],
  organisationId: null,
})

const form = ref(emptyForm())
const originalStatus = ref('config')
const hasTwintQr = ref(false)
const twintQrPreviewUrl = ref('')
const twintQrBusy = ref(false)
const copyBusy = ref(false)

const showTwintQrSection = computed(() =>
  Array.isArray(form.value.paymentTypes) && form.value.paymentTypes.includes('twint')
)

const organisationOptions = computed(() =>
  organisations.value.map((org) => ({ value: org.id, label: org.name }))
)

const canCreateEvents = computed(() => organisationOptions.value.length > 0)

const canSave = computed(() => {
  return !!(
    form.value.name &&
    form.value.status &&
    form.value.start &&
    form.value.end &&
    form.value.currency &&
    form.value.organisationId &&
    Array.isArray(form.value.paymentTypes) &&
    form.value.paymentTypes.length > 0
  )
})

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

function statusSeverity(status) {
  return {
    config: 'secondary',
    test: 'info',
    prod: 'success',
    archive: 'warn',
  }[status] || 'secondary'
}

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

async function fetchOrganisations() {
  try {
    const response = await apiFetch('/events/organisations')
    if (response.ok) {
      organisations.value = await response.json()
    }
  } catch (error) {
    message.value = 'Organisationen konnten nicht geladen werden.'
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

function resetForm() {
  editMode.value = false
  activeId.value = null
  showDetail.value = false
  hasTwintQr.value = false
  revokeTwintQrPreview()
  form.value = emptyForm()
  originalStatus.value = 'config'
  if (props.activeOrganisationId) {
    form.value.organisationId = props.activeOrganisationId
  } else if (organisationOptions.value.length === 1) {
    form.value.organisationId = organisationOptions.value[0].value
  }
  message.value = ''
}

function openCreateForm() {
  resetForm()
  showDetail.value = true
}

async function editEvent(event) {
  showDetail.value = true
  editMode.value = true
  activeId.value = event.id
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
    organisationId: event.organisation_id || null,
  }
  originalStatus.value = event.status || 'config'
  message.value = ''
  if (hasTwintQr.value) await loadTwintQrPreview()
}

function defaultCopyName(name) {
  const base = (name || '').trim() || 'Event'
  const suffix = ' (Kopie)'
  return base.endsWith(suffix) ? base : `${base}${suffix}`
}

async function copyEvent() {
  if (!activeId.value) return
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
    await editEvent(created)
    message.value = `Veranstaltung «${created.name}» erstellt.`
    messageType.value = 'success'
  } catch {
    message.value = 'Event konnte nicht kopiert werden.'
    messageType.value = 'error'
  } finally {
    copyBusy.value = false
  }
}

async function saveEvent() {
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
    organisation_id: form.value.organisationId,
    payment_mode: form.value.paymentMode,
    payment_types: form.value.paymentTypes,
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
    await fetchEvents()
    resetForm()
    message.value = wasEdit ? 'Veranstaltung aktualisiert.' : 'Veranstaltung erstellt.'
    messageType.value = 'success'
  } catch (error) {
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
  } catch (error) {
    message.value = 'Veranstaltung konnte nicht gelöscht werden.'
    messageType.value = 'error'
  }
}

onMounted(async () => {
  await fetchOrganisations()
  await fetchEvents()
})

onUnmounted(() => {
  revokeTwintQrPreview()
})
</script>

<style scoped>
h2 {
  margin: 0 0 1.5rem;
  color: var(--p-text-color);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

label {
  color: var(--p-text-color);
  font-size: 0.875rem;
  font-weight: 600;
}

small {
  color: var(--p-text-muted-color);
}

:deep(.p-inputtext),
:deep(.p-select),
:deep(.p-datepicker) {
  width: 100%;
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
  color: var(--p-text-muted-color);
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
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
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
  .field-row,
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
