<template>
  <ListDetailLayout
    title="Geräte"
    subtitle="Server, Drucker, mobile Geräte und weitere Installationen verwalten."
    createLabel="Neues Gerät"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? 'Gerät bearbeiten' : 'Neues Gerät' }}</h2>
      <div class="form-field">
        <label>Typ</label>
        <Select v-model="form.type" :options="typeOptions" optionLabel="label" optionValue="value" placeholder="Typ wählen" />
      </div>

      <div v-if="isAutoNamed" class="form-field">
        <label>Name</label>
        <InputText
          :value="form.name || 'Wird beim Speichern automatisch vergeben'"
          disabled
          class="input-readonly"
        />
        <small>{{ autoNameHint }}</small>
      </div>

      <div v-else-if="form.type" class="form-field">
        <label>Name <span class="optional">(optional)</span></label>
        <InputText v-model="form.name" placeholder="Anzeigename" />
      </div>

      <div v-if="isPrinter" class="form-field">
        <label>IP-Adresse</label>
        <InputText v-model="form.ip_address" placeholder="192.168.1.10" />
      </div>

      <div class="form-field">
        <label>Modell <span class="optional">(optional)</span></label>
        <InputText v-model="form.model" placeholder="z. B. HP LaserJet Pro" />
      </div>

      <div class="form-field">
        <label>Bemerkung <span class="optional">(optional)</span></label>
        <Textarea v-model="form.comment" rows="3" placeholder="Notizen zum Gerät" />
      </div>

      <div class="actions">
        <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
        <Button
          label="Speichern"
          class="primary-button"
          :disabled="!form.type"
          @click="saveAppliance"
        />
      </div>

      <div v-if="edgeCredentialsRevealed" class="edge-credentials-panel">
        <h3>Edge-Zugangsdaten (einmalig)</h3>
        <p class="edge-credentials-warning">
          Speichern Sie den Schlüssel jetzt (z.&nbsp;B. für <code>EDGE_CLIENT_ID</code> und <code>EDGE_SECRET</code> auf dem Pi).
          Er wird nicht erneut angezeigt. Eine Neuausstellung macht den bisherigen Schlüssel ungültig.
        </p>
        <div class="form-field">
          <label>Edge-Client-ID</label>
          <div class="edge-copy-row">
            <InputText :value="edgeCredentialsRevealed.clientId" readonly class="input-readonly edge-secret-input" />
            <Button
              type="button"
              label="Kopieren"
              class="secondary-button"
              @click="copyEdgeField('Edge-Client-ID', edgeCredentialsRevealed.clientId)"
            />
          </div>
        </div>
        <div class="form-field">
          <label>Edge-Geheimnis</label>
          <div class="edge-copy-row">
            <InputText :value="edgeCredentialsRevealed.secret" readonly class="input-readonly edge-secret-input" />
            <Button
              type="button"
              label="Kopieren"
              class="secondary-button"
              @click="copyEdgeField('Edge-Geheimnis', edgeCredentialsRevealed.secret)"
            />
          </div>
        </div>
        <Button type="button" label="Anzeige schließen" class="secondary-button" @click="clearEdgeCredentialsReveal" />
      </div>

      <template v-if="editMode && applianceDetail">
        <div v-if="applianceDetail.type === 'server'" class="lending-section edge-server-section">
          <h3>Edge-Anbindung (On-Prem / Pi)</h3>
          <p class="edge-credentials-hint">
            Die Client-ID können Sie jederzeit kopieren; das Geheimnis nur direkt nach Erstellung oder Neuausstellung (siehe Kasten oben).
          </p>
          <div class="form-field">
            <label>Edge-Client-ID</label>
            <div class="edge-copy-row">
              <InputText
                :value="applianceDetail.edge_client_id || '—'"
                readonly
                class="input-readonly edge-secret-input"
              />
              <Button
                v-if="applianceDetail.edge_client_id"
                type="button"
                label="Kopieren"
                class="secondary-button"
                @click="copyEdgeField('Edge-Client-ID', applianceDetail.edge_client_id)"
              />
            </div>
          </div>
          <Button
            type="button"
            label="Edge-Zugangsdaten neu ausgeben"
            class="secondary-button"
            @click="rotateEdgeCredentials"
          />
        </div>

        <div class="lending-section">
          <h3>Ausleihen</h3>
          <p v-if="lendingStatusLent" class="lending-hint">
            Dieses Gerät ist aktuell ausgeliehen. Weitere Ausleihen sind nur möglich, wenn sich die Zeiträume nicht mit einer offenen Ausleihe überschneiden (z. B. geplante Ausleihe nach Ende der aktuellen Periode).
          </p>
          <div class="lending-form">
            <div class="form-field">
              <label>Organisation</label>
              <Select
                v-model="lendForm.organisationId"
                :options="organisationOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Organisation wählen"
                :disabled="!organisationOptions.length"
              />
            </div>
            <div class="form-field">
              <label>Startdatum</label>
              <DatePicker
                v-model="lendForm.startDate"
                showIcon
                dateFormat="dd.mm.yy"
                placeholder="Startdatum"
              />
            </div>
            <div class="form-field">
              <label>Tage</label>
              <InputNumber v-model="lendForm.durationDays" :min="1" :max="3650" showButtons />
            </div>
            <Button
              label="Ausleihen"
              class="primary-button"
              type="button"
              :disabled="!canSubmitLend"
              @click="submitLend"
            />
          </div>
          <p v-if="lendingMessage" :class="lendingMessageType">{{ lendingMessage }}</p>
        </div>

        <div class="lending-section">
          <h3>Historie</h3>
          <DataTable :value="applianceDetail.lendings || []" dataKey="id" class="lendings-table" responsiveLayout="scroll">
            <template #empty>Keine Ausleihen.</template>
            <Column field="organisation_name" header="Organisation" />
            <Column field="start_date" header="Von">
              <template #body="{ data }">{{ formatDeDate(data.start_date) }}</template>
            </Column>
            <Column field="end_date" header="Bis">
              <template #body="{ data }">{{ formatDeDate(data.end_date) }}</template>
            </Column>
            <Column header="Status">
              <template #body="{ data }">{{ lendingHistoryStatusLabel(data) }}</template>
            </Column>
            <Column header="Aktion">
              <template #body="{ data }">
                <Button
                  v-if="data.segment === 'current' && !data.returned_at"
                  label="Zurückgeben"
                  class="secondary-button"
                  type="button"
                  @click="returnLending(data.id)"
                />
                <Button
                  v-else-if="data.segment === 'future'"
                  label="Stornieren"
                  class="secondary-button"
                  type="button"
                  :disabled="cancellingLendingId === data.id"
                  @click="cancelPlannedLendingRow(data.id)"
                />
                <span v-else>—</span>
              </template>
            </Column>
          </DataTable>
        </div>
      </template>

      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <div class="table-header">
        <h2>Alle Geräte</h2>
        <span>{{ filteredAppliances.length }} von {{ appliances.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="searchQuery" placeholder="Name, Typ, IP, Modell oder Bemerkung suchen..." />
          </IconField>
        </div>
        <div class="filter-field">
          <label>Typ</label>
          <Select v-model="typeFilter" :options="typeFilterOptions" optionLabel="label" optionValue="value" placeholder="Alle Typen" />
        </div>
        <div class="filter-field">
          <label>IP-Adresse</label>
          <Select v-model="ipFilter" :options="ipFilterOptions" optionLabel="label" optionValue="value" placeholder="Alle" />
        </div>
      </div>
      <DataTable
        :value="paginatedAppliances"
        dataKey="id"
        responsiveLayout="scroll"
        class="list-table"
        @row-click="editAppliance($event.data)"
      >
        <template #empty>Keine Geräte gefunden.</template>
        <Column field="id" header="ID" />
        <Column field="name" header="Name">
          <template #body="{ data }">{{ data.name || '—' }}</template>
        </Column>
        <Column field="type" header="Typ">
          <template #body="{ data }">{{ typeLabel(data.type) }}</template>
        </Column>
        <Column header="Status">
          <template #body="{ data }">
            <Tag :value="lendingStatusLabel(data.lending_status)" :severity="data.lending_status === 'lent' ? 'warn' : 'success'" />
          </template>
        </Column>
        <Column header="Organisation">
          <template #body="{ data }">{{ data.current_lending?.organisation_name || '—' }}</template>
        </Column>
        <Column header="Bis">
          <template #body="{ data }">{{
            data.current_lending?.end_date ? formatDeDate(data.current_lending.end_date) : '—'
          }}</template>
        </Column>
        <Column field="ip_address" header="IP">
          <template #body="{ data }">{{ data.type === 'printer' ? data.ip_address || '—' : '—' }}</template>
        </Column>
        <Column field="model" header="Modell">
          <template #body="{ data }">
            <span class="cell-truncate" :title="data.model || ''">{{ data.model || '—' }}</span>
          </template>
        </Column>
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button label="Löschen" class="danger" @click.stop="deleteAppliance(data.id)" />
          </template>
        </Column>
      </DataTable>
      <div v-if="filteredAppliances.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <Paginator
          :first="(currentPage - 1) * pageSize"
          :rows="pageSize"
          :totalRecords="filteredAppliances.length"
          @page="currentPage = $event.page + 1"
        />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiFetch } from '../api'
import { parseApiErrorDetail } from '../utils/apiError'
import { cancelPlannedLendingForAppliance } from '../utils/applianceLending'

const appliances = ref([])
const showDetail = ref(false)
const editMode = ref(false)
const activeId = ref(null)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const typeFilter = ref('')
const ipFilter = ref('')
const currentPage = ref(1)
const pageSize = 20

const organisations = ref([])
const applianceDetail = ref(null)
const lendingMessage = ref('')
const lendingMessageType = ref('')
const cancellingLendingId = ref(null)
/** Einmalige Anzeige nach POST /appliances (Server) oder POST .../edge-credentials */
const edgeCredentialsRevealed = ref(null)
const lendForm = ref({
  organisationId: null,
  startDate: null,
  durationDays: 7,
})

const emptyForm = () => ({
  type: '',
  name: '',
  ip_address: '',
  model: '',
  comment: '',
})

const form = ref(emptyForm())

const isPrinter = computed(() => form.value.type === 'printer')
const isAutoNamed = computed(() => form.value.type === 'server' || form.value.type === 'printer')

const autoNameHint = computed(() => {
  if (form.value.type === 'server') {
    return 'Server erhalten automatisch den Namen eines griechischen Gottes.'
  }
  if (form.value.type === 'printer') {
    return 'Drucker erhalten automatisch den Namen einer Hauptstadt.'
  }
  return ''
})

const TYPE_LABELS = {
  server: 'Server',
  printer: 'Drucker',
  mobile: 'Mobil',
  tablet: 'Tablet',
  router: 'Router',
  ap: 'Access Point',
}

const typeOptions = Object.entries(TYPE_LABELS).map(([value, label]) => ({ value, label }))
const typeFilterOptions = [{ value: '', label: 'Alle Typen' }, ...typeOptions]
const ipFilterOptions = [
  { value: '', label: 'Alle' },
  { value: 'with-ip', label: 'Mit IP' },
  { value: 'without-ip', label: 'Ohne IP' },
]

const organisationOptions = computed(() =>
  organisations.value.map((o) => ({ label: o.name, value: o.id })),
)

const lendingStatusLent = computed(() => applianceDetail.value?.lending_status === 'lent')

const canSubmitLend = computed(() => {
  if (!lendForm.value.organisationId || !lendForm.value.startDate) return false
  const d = lendForm.value.durationDays
  return typeof d === 'number' && d >= 1
})

function typeLabel(type) {
  return TYPE_LABELS[type] || type
}

function matchesSearch(device, term) {
  if (!term) return true
  return [
    device.id,
    device.name,
    typeLabel(device.type),
    device.type,
    device.ip_address,
    device.model,
    device.comment,
    device.current_lending?.organisation_name,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

function lendingStatusLabel(status) {
  return status === 'lent' ? 'Ausgeliehen' : 'Verfügbar'
}

function lendingHistoryStatusLabel(row) {
  if (row.returned_at) return 'Zurückgegeben'
  if (row.segment === 'current') return 'Aktiv'
  if (row.segment === 'future') return 'Geplant'
  return 'Abgelaufen'
}

function formatDeDate(iso) {
  if (!iso) return '—'
  const [y, m, d] = String(iso).split('T')[0].split('-').map(Number)
  if (!y || !m || !d) return iso
  return new Date(y, m - 1, d).toLocaleDateString('de-DE')
}

function toIsoDate(d) {
  if (!d) return null
  const x = d instanceof Date ? d : new Date(d)
  const y = x.getFullYear()
  const mo = String(x.getMonth() + 1).padStart(2, '0')
  const day = String(x.getDate()).padStart(2, '0')
  return `${y}-${mo}-${day}`
}

const filteredAppliances = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return appliances.value.filter((device) => {
    if (!matchesSearch(device, term)) return false
    if (typeFilter.value && device.type !== typeFilter.value) return false
    const hasIp = !!device.ip_address
    if (ipFilter.value === 'with-ip' && !hasIp) return false
    if (ipFilter.value === 'without-ip' && hasIp) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredAppliances.value.length / pageSize)))

const paginatedAppliances = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredAppliances.value.slice(start, start + pageSize)
})

const paginationLabel = computed(() => {
  if (!filteredAppliances.value.length) return '0 Einträge'
  const start = (currentPage.value - 1) * pageSize + 1
  const end = Math.min(currentPage.value * pageSize, filteredAppliances.value.length)
  return `${start}-${end} von ${filteredAppliances.value.length}`
})

watch([searchQuery, typeFilter, ipFilter], () => {
  currentPage.value = 1
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

async function fetchAppliances() {
  try {
    const response = await apiFetch('/appliances/')
    appliances.value = await response.json()
  } catch (error) {
    message.value = 'Geräte konnten nicht geladen werden.'
    messageType.value = 'error'
  }
}

async function fetchOrganisations() {
  try {
    const response = await apiFetch('/organisations/')
    organisations.value = await response.json()
  } catch {
    organisations.value = []
  }
}

async function fetchApplianceDetail(id) {
  lendingMessage.value = ''
  try {
    const response = await apiFetch(`/appliances/${id}`)
    if (!response.ok) throw new Error(await response.text())
    applianceDetail.value = await response.json()
  } catch {
    applianceDetail.value = null
    lendingMessage.value = 'Ausleihen-Details konnten nicht geladen werden.'
    lendingMessageType.value = 'error'
  }
}

function resetLendForm() {
  lendForm.value = {
    organisationId: null,
    startDate: null,
    durationDays: 7,
  }
}

function clearEdgeCredentialsReveal() {
  edgeCredentialsRevealed.value = null
}

async function copyEdgeField(label, text) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    message.value = `${label} in die Zwischenablage kopiert.`
    messageType.value = 'success'
  } catch {
    message.value = 'Kopieren in die Zwischenablage nicht möglich.'
    messageType.value = 'error'
  }
}

function resetForm() {
  editMode.value = false
  activeId.value = null
  showDetail.value = false
  form.value = emptyForm()
  message.value = ''
  applianceDetail.value = null
  resetLendForm()
  lendingMessage.value = ''
  clearEdgeCredentialsReveal()
}

function openCreateForm() {
  resetForm()
  showDetail.value = true
}

function editAppliance(device) {
  showDetail.value = true
  editMode.value = true
  activeId.value = device.id
  clearEdgeCredentialsReveal()
  form.value = {
    type: device.type,
    name: device.name || '',
    ip_address: device.ip_address || '',
    model: device.model || '',
    comment: device.comment || '',
  }
  message.value = ''
  resetLendForm()
  fetchApplianceDetail(device.id)
}

function buildPayload() {
  const payload = {
    type: form.value.type,
    model: form.value.model?.trim() || null,
    comment: form.value.comment?.trim() || null,
  }
  if (form.value.type === 'printer') {
    payload.ip_address = form.value.ip_address?.trim() || null
  }
  if (!isAutoNamed.value && form.value.name?.trim()) {
    payload.name = form.value.name.trim()
  }
  return payload
}

async function saveAppliance() {
  const payload = buildPayload()

  try {
    const path = editMode.value ? `/appliances/${activeId.value}` : '/appliances/'
    const method = editMode.value ? 'PUT' : 'POST'
    const response = await apiFetch(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      throw new Error(await response.text())
    }
    const wasEdit = editMode.value
    const body = await response.json()
    const savedId = wasEdit ? activeId.value : body.id
    await fetchAppliances()
    if (wasEdit && savedId) {
      await fetchApplianceDetail(savedId)
    } else if (body.type === 'server' && body.edge_secret) {
      editMode.value = true
      activeId.value = body.id
      form.value = {
        type: body.type,
        name: body.name || '',
        ip_address: body.ip_address || '',
        model: body.model || '',
        comment: body.comment || '',
      }
      edgeCredentialsRevealed.value = {
        clientId: body.edge_client_id,
        secret: body.edge_secret,
      }
      await fetchApplianceDetail(body.id)
    } else {
      resetForm()
    }
    message.value = wasEdit ? 'Gerät aktualisiert.' : 'Gerät erstellt.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Fehler beim Speichern des Geräts.'
    messageType.value = 'error'
  }
}

async function rotateEdgeCredentials() {
  if (!activeId.value || applianceDetail.value?.type !== 'server') return
  if (
    !confirm(
      'Neue Edge-Zugangsdaten ausgeben? Der bisherige Schlüssel funktioniert danach nicht mehr (z. B. Pi .env anpassen).',
    )
  ) {
    return
  }
  try {
    const response = await apiFetch(`/appliances/${activeId.value}/edge-credentials`, {
      method: 'POST',
    })
    if (!response.ok) {
      message.value = await parseApiErrorDetail(response)
      messageType.value = 'error'
      return
    }
    const body = await response.json()
    edgeCredentialsRevealed.value = {
      clientId: body.edge_client_id,
      secret: body.edge_secret,
    }
    await fetchApplianceDetail(activeId.value)
    await fetchAppliances()
    form.value = {
      type: body.type,
      name: body.name || '',
      ip_address: body.ip_address || '',
      model: body.model || '',
      comment: body.comment || '',
    }
    message.value = 'Neue Edge-Zugangsdaten wurden ausgegeben.'
    messageType.value = 'success'
  } catch {
    message.value = 'Edge-Zugangsdaten konnten nicht neu ausgegeben werden.'
    messageType.value = 'error'
  }
}

async function deleteAppliance(id) {
  if (!confirm('Gerät wirklich löschen?')) {
    return
  }
  try {
    const response = await apiFetch(`/appliances/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error(await response.text())
    }
    await fetchAppliances()
    message.value = 'Gerät gelöscht.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Gerät konnte nicht gelöscht werden.'
    messageType.value = 'error'
  }
}

async function submitLend() {
  if (!activeId.value || !canSubmitLend.value) return
  lendingMessage.value = ''
  try {
    const response = await apiFetch(`/appliances/${activeId.value}/lendings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        organisation_id: lendForm.value.organisationId,
        start_date: toIsoDate(lendForm.value.startDate),
        duration_days: lendForm.value.durationDays,
      }),
    })
    if (!response.ok) {
      lendingMessage.value = await parseApiErrorDetail(response)
      lendingMessageType.value = 'error'
      return
    }
    applianceDetail.value = await response.json()
    await fetchAppliances()
    resetLendForm()
    lendingMessage.value = 'Ausleihe angelegt.'
    lendingMessageType.value = 'success'
  } catch {
    lendingMessage.value = 'Ausleihe konnte nicht angelegt werden.'
    lendingMessageType.value = 'error'
  }
}

async function returnLending(lendingId) {
  if (!activeId.value) return
  lendingMessage.value = ''
  try {
    const response = await apiFetch(
      `/appliances/${activeId.value}/lendings/${lendingId}/return`,
      { method: 'POST' },
    )
    if (!response.ok) {
      throw new Error(await response.text())
    }
    applianceDetail.value = await response.json()
    await fetchAppliances()
    lendingMessage.value = 'Gerät zurückgenommen.'
    lendingMessageType.value = 'success'
  } catch {
    lendingMessage.value = 'Rückgabe fehlgeschlagen.'
    lendingMessageType.value = 'error'
  }
}

async function cancelPlannedLendingRow(lendingId) {
  if (!activeId.value) return
  if (!confirm('Geplante Ausleihe wirklich stornieren?')) return
  cancellingLendingId.value = lendingId
  lendingMessage.value = ''
  try {
    await cancelPlannedLendingForAppliance(activeId.value, lendingId)
    await fetchApplianceDetail(activeId.value)
    await fetchAppliances()
    lendingMessage.value = 'Geplante Ausleihe storniert.'
    lendingMessageType.value = 'success'
  } catch (e) {
    lendingMessage.value = e.message || 'Stornierung fehlgeschlagen.'
    lendingMessageType.value = 'error'
  } finally {
    cancellingLendingId.value = null
  }
}

onMounted(() => {
  fetchAppliances()
  fetchOrganisations()
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

label {
  color: var(--p-text-color);
  font-size: 0.875rem;
  font-weight: 600;
}

.optional,
small {
  color: var(--p-text-muted-color);
  font-weight: 400;
}

:deep(.p-inputtext),
:deep(.p-select),
:deep(.p-password),
:deep(.p-textarea),
:deep(.p-inputnumber),
:deep(.p-datepicker) {
  width: 100%;
}

textarea {
  resize: vertical;
}

.input-readonly {
  opacity: 0.75;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.lending-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--p-content-border-color);
}

.edge-credentials-panel {
  margin-top: 1.5rem;
  padding: 1.25rem;
  border: 1px solid var(--p-primary-color);
  border-radius: var(--p-border-radius-lg);
  background: var(--p-primary-50, color-mix(in srgb, var(--p-primary-color) 8%, transparent));
}

.edge-credentials-panel h3 {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
  color: var(--p-text-color);
}

.edge-credentials-warning {
  margin: 0 0 1rem;
  color: var(--p-text-color);
  font-size: 0.9rem;
  line-height: 1.45;
}

.edge-credentials-warning code {
  font-size: 0.85em;
}

.edge-credentials-hint {
  color: var(--p-text-muted-color);
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  line-height: 1.4;
}

.edge-copy-row {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;
}

.edge-copy-row .edge-secret-input {
  flex: 1;
  min-width: 0;
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
}

.edge-server-section {
  margin-top: 1.5rem;
}

.lending-section h3 {
  margin: 0 0 1rem;
  font-size: 1.05rem;
  color: var(--p-text-color);
}

.lending-hint {
  color: var(--p-text-muted-color);
  margin: 0 0 0.75rem;
}

.lending-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.lendings-table {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-lg);
  overflow: hidden;
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
  grid-template-columns: minmax(240px, 1fr) 180px 180px;
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

.cell-truncate {
  display: inline-block;
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
  white-space: nowrap;
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
