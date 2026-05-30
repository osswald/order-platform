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
        <v-select
          v-model="form.type"
          :items="typeOptions"
          item-title="label"
          item-value="value"
          label="Typ"
          placeholder="Typ wählen"
          hide-details="auto"
        />
      </div>

      <div v-if="isAutoNamed" class="form-field">
        <v-text-field
          :model-value="form.name || 'Wird beim Speichern automatisch vergeben'"
          label="Name"
          disabled
          hide-details="auto"
        />
        <small>{{ autoNameHint }}</small>
      </div>

      <div v-else-if="form.type" class="form-field">
        <v-text-field v-model="form.name" label="Name (optional)" placeholder="Anzeigename" hide-details="auto" />
      </div>

      <div v-if="isPrinter" class="form-field">
        <v-text-field v-model="form.ip_address" label="IP-Adresse" placeholder="192.168.1.10" hide-details="auto" />
      </div>

      <div class="form-field">
        <v-text-field v-model="form.model" label="Modell (optional)" placeholder="z. B. HP LaserJet Pro" hide-details="auto" />
      </div>

      <div class="form-field">
        <v-textarea v-model="form.comment" label="Bemerkung (optional)" rows="3" placeholder="Notizen zum Gerät" hide-details="auto" />
      </div>

      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
        <v-btn color="primary" :disabled="!form.type" @click="saveAppliance">Speichern</v-btn>
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
            <v-text-field
              :model-value="edgeCredentialsRevealed.clientId"
              readonly
              hide-details
              class="edge-secret-input"
            />
            <v-btn variant="outlined" type="button" @click="copyEdgeField('Edge-Client-ID', edgeCredentialsRevealed.clientId)">
              Kopieren
            </v-btn>
          </div>
        </div>
        <div class="form-field">
          <label>Edge-Geheimnis</label>
          <div class="edge-copy-row">
            <v-text-field
              :model-value="edgeCredentialsRevealed.secret"
              readonly
              hide-details
              class="edge-secret-input"
            />
            <v-btn variant="outlined" type="button" @click="copyEdgeField('Edge-Geheimnis', edgeCredentialsRevealed.secret)">
              Kopieren
            </v-btn>
          </div>
        </div>
        <v-btn variant="outlined" type="button" @click="clearEdgeCredentialsReveal">Anzeige schließen</v-btn>
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
              <v-text-field
                :model-value="applianceDetail.edge_client_id || '—'"
                readonly
                hide-details
                class="edge-secret-input"
              />
              <v-btn
                v-if="applianceDetail.edge_client_id"
                variant="outlined"
                type="button"
                @click="copyEdgeField('Edge-Client-ID', applianceDetail.edge_client_id)"
              >
                Kopieren
              </v-btn>
            </div>
          </div>
          <v-btn variant="outlined" type="button" @click="rotateEdgeCredentials">
            Edge-Zugangsdaten neu ausgeben
          </v-btn>

          <div class="pairing-panel">
            <h4>Raspberry Pi SD-Karten</h4>
            <p class="edge-credentials-hint">
              Jede gekoppelte SD-Karte erhält eigene Zugangsdaten. Es darf immer nur eine Karte pro Server aktiv laufen.
            </p>
            <v-btn color="primary" type="button" :disabled="pairingLoading" @click="createPairingSession">
              Kopplungscode für weitere SD-Karte erzeugen
            </v-btn>
            <div v-if="pairingSession" class="pairing-code-card">
              <span class="pairing-code-label">Kopplungscode</span>
              <strong>{{ pairingSession.pairing_code_display }}</strong>
              <p>
                Öffnen Sie <code>{{ pairingSession.setup_url }}</code> auf der neuen SD-Karte und geben Sie diesen Code ein.
                Gültig bis {{ formatDeDateTime(pairingSession.expires_at) }}.
              </p>
            </div>
            <p v-if="pairingMessage" :class="pairingMessageType">{{ pairingMessage }}</p>

            <VqDataTable
              :headers="edgeCredentialsHeaders"
              :items="applianceDetail.edge_credentials || []"
              item-value="id"
              class="vq-data-table edge-installations-table"
              hide-default-footer
            >
              <template #item.label="{ item }">{{ item.label || `SD-Karte ${item.id}` }}</template>
              <template #item.edge_client_id="{ item }">
                <span class="cell-truncate" :title="item.edge_client_id">{{ item.edge_client_id }}</span>
              </template>
              <template #item.status="{ item }">
                <v-chip
                  :color="item.status === 'active' ? 'success' : 'error'"
                  size="small"
                  variant="tonal"
                >
                  {{ item.status === 'active' ? 'Aktiv' : 'Gesperrt' }}
                </v-chip>
              </template>
              <template #item.last_seen_at="{ item }">{{ formatDeDateTime(item.last_seen_at) }}</template>
              <template #item.actions="{ item }">
                <v-btn
                  v-if="item.status === 'active'"
                  variant="outlined"
                  size="small"
                  type="button"
                  @click="revokeEdgeCredential(item.id)"
                >
                  Sperren
                </v-btn>
                <span v-else>—</span>
              </template>
              <template #no-data>Keine gekoppelten SD-Karten.</template>
            </VqDataTable>
          </div>
        </div>

        <div class="lending-section">
          <h3>Ausleihen</h3>
          <p v-if="lendingStatusLent" class="lending-hint">
            Dieses Gerät ist aktuell ausgeliehen. Weitere Ausleihen sind nur möglich, wenn sich die Zeiträume nicht mit einer offenen Ausleihe überschneiden (z. B. geplante Ausleihe nach Ende der aktuellen Periode).
          </p>
          <div class="lending-form">
            <div class="form-field">
              <v-select
                v-model="lendForm.organisationId"
                :items="organisationOptions"
                item-title="label"
                item-value="value"
                label="Organisation"
                placeholder="Organisation wählen"
                :disabled="!organisationOptions.length"
                hide-details="auto"
              />
            </div>
            <div class="form-field">
              <v-menu v-model="lendStartMenuOpen" :close-on-content-click="false">
                <template #activator="{ props: menuProps }">
                  <v-text-field
                    :model-value="lendForm.startDate ? formatDeDate(toIsoDate(lendForm.startDate)) : ''"
                    label="Startdatum"
                    placeholder="Startdatum"
                    prepend-inner-icon="mdi-calendar"
                    readonly
                    hide-details="auto"
                    v-bind="menuProps"
                  />
                </template>
                <v-date-picker
                  v-model="lendForm.startDate"
                  @update:model-value="lendStartMenuOpen = false"
                />
              </v-menu>
            </div>
            <div class="form-field">
              <v-text-field
                v-model.number="lendForm.durationDays"
                type="number"
                :min="1"
                :max="3650"
                label="Tage"
                hide-details="auto"
              />
            </div>
            <v-btn color="primary" type="button" :disabled="!canSubmitLend" @click="submitLend">
              Ausleihen
            </v-btn>
          </div>
          <p v-if="lendingMessage" :class="lendingMessageType">{{ lendingMessage }}</p>
        </div>

        <div class="lending-section">
          <h3>Historie</h3>
          <VqDataTable
            :headers="lendingHistoryHeaders"
            :items="applianceDetail.lendings || []"
            item-value="id"
            class="vq-data-table lendings-table"
            hide-default-footer
          >
            <template #item.start_date="{ item }">{{ formatDeDate(item.start_date) }}</template>
            <template #item.end_date="{ item }">{{ formatDeDate(item.end_date) }}</template>
            <template #item.status="{ item }">{{ lendingHistoryStatusLabel(item) }}</template>
            <template #item.actions="{ item }">
              <v-btn
                v-if="item.segment === 'current' && !item.returned_at"
                variant="outlined"
                size="small"
                type="button"
                @click="returnLending(item.id)"
              >
                Zurückgeben
              </v-btn>
              <v-btn
                v-else-if="item.segment === 'future'"
                variant="outlined"
                size="small"
                type="button"
                :disabled="cancellingLendingId === item.id"
                @click="cancelPlannedLendingRow(item.id)"
              >
                Stornieren
              </v-btn>
              <span v-else>—</span>
            </template>
            <template #no-data>Keine Ausleihen.</template>
          </VqDataTable>
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
          <v-text-field
            v-model="searchQuery"
            label="Suche"
            prepend-inner-icon="mdi-magnify"
            placeholder="Name, Typ, IP, Modell oder Bemerkung suchen..."
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="typeFilter"
            :items="typeFilterOptions"
            item-title="label"
            item-value="value"
            label="Typ"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="ipFilter"
            :items="ipFilterOptions"
            item-title="label"
            item-value="value"
            label="IP-Adresse"
            hide-details
            density="compact"
          />
        </div>
      </div>
      <VqDataTable
        :headers="tableHeaders"
        :items="paginatedAppliances"
        item-value="id"
        class="vq-data-table list-table"
        hide-default-footer
        hover
        @click:row="(_, { item }) => editAppliance(item)"
      >
        <template #item.name="{ item }">{{ item.name || '—' }}</template>
        <template #item.type="{ item }">{{ typeLabel(item.type) }}</template>
        <template #item.lending_status="{ item }">
          <v-chip
            :color="item.lending_status === 'lent' ? 'warning' : 'success'"
            size="small"
            variant="tonal"
          >
            {{ lendingStatusLabel(item.lending_status) }}
          </v-chip>
        </template>
        <template #item.organisation="{ item }">{{ item.current_lending?.organisation_name || '—' }}</template>
        <template #item.end_date="{ item }">
          {{ item.current_lending?.end_date ? formatDeDate(item.current_lending.end_date) : '—' }}
        </template>
        <template #item.ip_address="{ item }">
          {{ item.type === 'printer' ? item.ip_address || '—' : '—' }}
        </template>
        <template #item.model="{ item }">
          <span class="cell-truncate" :title="item.model || ''">{{ item.model || '—' }}</span>
        </template>
        <template #item.actions="{ item }">
          <v-btn color="error" variant="outlined" size="small" @click.stop="deleteAppliance(item.id)">
            Löschen
          </v-btn>
        </template>
        <template #no-data>Keine Geräte gefunden.</template>
      </VqDataTable>
      <div v-if="filteredAppliances.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" density="compact" />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiFetch } from '../api'
import { parseApiErrorDetail } from '../utils/apiError'
import { cancelPlannedLendingForAppliance } from '../utils/applianceLending'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import VqDataTable from './VqDataTable.vue'

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('appliances')

const appliances = ref([])
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const typeFilter = ref('')
const ipFilter = ref('')
const currentPage = ref(1)
const pageSize = 20
const lendStartMenuOpen = ref(false)

const tableHeaders = [
  { title: 'ID', key: 'id' },
  { title: 'Name', key: 'name', sortable: false },
  { title: 'Typ', key: 'type', sortable: false },
  { title: 'Status', key: 'lending_status', sortable: false },
  { title: 'Organisation', key: 'organisation', sortable: false },
  { title: 'Bis', key: 'end_date', sortable: false },
  { title: 'IP', key: 'ip_address', sortable: false },
  { title: 'Modell', key: 'model', sortable: false },
  { title: 'Aktionen', key: 'actions', sortable: false, align: 'end' },
]

const edgeCredentialsHeaders = [
  { title: 'SD-Karte', key: 'label', sortable: false },
  { title: 'Client-ID', key: 'edge_client_id', sortable: false },
  { title: 'Status', key: 'status', sortable: false },
  { title: 'Zuletzt online', key: 'last_seen_at', sortable: false },
  { title: 'Aktion', key: 'actions', sortable: false, align: 'end' },
]

const lendingHistoryHeaders = [
  { title: 'Organisation', key: 'organisation_name' },
  { title: 'Von', key: 'start_date', sortable: false },
  { title: 'Bis', key: 'end_date', sortable: false },
  { title: 'Status', key: 'status', sortable: false },
  { title: 'Aktion', key: 'actions', sortable: false, align: 'end' },
]

const organisations = ref([])
const applianceDetail = ref(null)
const lendingMessage = ref('')
const lendingMessageType = ref('')
const pairingSession = ref(null)
const pairingMessage = ref('')
const pairingMessageType = ref('')
const pairingLoading = ref(false)
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

function formatDeDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('de-DE')
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

function clearDetailState() {
  form.value = emptyForm()
  message.value = ''
  applianceDetail.value = null
  pairingSession.value = null
  pairingMessage.value = ''
  resetLendForm()
  lendingMessage.value = ''
  clearEdgeCredentialsReveal()
}

function applyDeviceToForm(device) {
  clearEdgeCredentialsReveal()
  pairingSession.value = null
  pairingMessage.value = ''
  form.value = {
    type: device.type,
    name: device.name || '',
    ip_address: device.ip_address || '',
    model: device.model || '',
    comment: device.comment || '',
  }
  message.value = ''
  resetLendForm()
}

async function syncRouteToForm() {
  if (!showDetail.value) {
    clearDetailState()
    return
  }
  if (isCreateMode.value) {
    clearDetailState()
    return
  }
  const id = routeEntityId.value
  if (id == null) {
    goToList()
    return
  }
  let row = appliances.value.find((d) => Number(d.id) === Number(id))
  if (!row) {
    try {
      const response = await apiFetch(`/appliances/${id}`)
      if (!response.ok) throw new Error(await response.text())
      row = await response.json()
    } catch {
      message.value = 'Gerät nicht gefunden.'
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyDeviceToForm(row)
  await fetchApplianceDetail(id)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function editAppliance(device) {
  applyDeviceToForm(device)
  goToDetail(device.id)
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
      message.value = 'Gerät aktualisiert.'
      messageType.value = 'success'
    } else if (body.type === 'server' && body.edge_secret) {
      edgeCredentialsRevealed.value = {
        clientId: body.edge_client_id,
        secret: body.edge_secret,
      }
      message.value = 'Gerät erstellt.'
      messageType.value = 'success'
      await goToDetail(body.id)
      applyDeviceToForm(body)
      await fetchApplianceDetail(body.id)
    } else {
      message.value = 'Gerät erstellt.'
      messageType.value = 'success'
      await goToList()
    }
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

async function createPairingSession() {
  if (!activeId.value || applianceDetail.value?.type !== 'server') return
  pairingLoading.value = true
  pairingMessage.value = ''
  pairingSession.value = null
  try {
    const response = await apiFetch(`/appliances/${activeId.value}/pairing-sessions`, { method: 'POST' })
    if (!response.ok) {
      pairingMessage.value = await parseApiErrorDetail(response)
      pairingMessageType.value = 'error'
      return
    }
    pairingSession.value = await response.json()
    pairingMessage.value = 'Kopplungscode erzeugt.'
    pairingMessageType.value = 'success'
  } catch {
    pairingMessage.value = 'Kopplungscode konnte nicht erzeugt werden.'
    pairingMessageType.value = 'error'
  } finally {
    pairingLoading.value = false
  }
}

async function revokeEdgeCredential(credentialId) {
  if (!activeId.value || !credentialId) return
  if (!confirm('Diese SD-Karte wirklich sperren? Sie kann danach nicht mehr mit der Cloud synchronisieren.')) return
  try {
    const response = await apiFetch(`/appliances/${activeId.value}/edge-credentials/${credentialId}/revoke`, {
      method: 'POST',
    })
    if (!response.ok) {
      message.value = await parseApiErrorDetail(response)
      messageType.value = 'error'
      return
    }
    applianceDetail.value = await response.json()
    await fetchAppliances()
    message.value = 'SD-Karte wurde gesperrt.'
    messageType.value = 'success'
  } catch {
    message.value = 'SD-Karte konnte nicht gesperrt werden.'
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
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
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
  color: rgb(var(--v-theme-on-surface));
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

.optional,
small {
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-weight: 400;
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
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.edge-credentials-panel {
  margin-top: 1.5rem;
  padding: 1.25rem;
  border: 1px solid rgb(var(--v-theme-primary));
  border-radius: 8px;
  background: rgba(var(--v-theme-primary), 0.08);
}

.edge-credentials-panel h3 {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
  color: rgb(var(--v-theme-on-surface));
}

.edge-credentials-warning {
  margin: 0 0 1rem;
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.9rem;
  line-height: 1.45;
}

.edge-credentials-warning code {
  font-size: 0.85em;
}

.edge-credentials-hint {
  color: rgba(var(--v-theme-on-surface), 0.65);
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

.pairing-panel {
  margin-top: 1.25rem;
  padding: 1rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}

.pairing-panel h4 {
  margin: 0 0 0.75rem;
}

.pairing-code-card {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 8px;
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.pairing-code-label {
  display: block;
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}

.pairing-code-card strong {
  display: block;
  font-family: ui-monospace, monospace;
  font-size: 1.75rem;
  letter-spacing: 0.08em;
  margin-bottom: 0.5rem;
}

.pairing-code-card p {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.65);
  line-height: 1.4;
}

.lending-section h3 {
  margin: 0 0 1rem;
  font-size: 1.05rem;
  color: rgb(var(--v-theme-on-surface));
}

.lending-hint {
  color: rgba(var(--v-theme-on-surface), 0.65);
  margin: 0 0 0.75rem;
}

.lending-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.lendings-table {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
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
  color: rgba(var(--v-theme-on-surface), 0.65);
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
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
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
