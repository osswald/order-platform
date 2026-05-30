<template>
  <ListDetailLayout
    title="Organisationen"
    subtitle="Veranstalter verwalten und Benutzer zuordnen."
    createLabel="Neue Organisation"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? 'Organisation bearbeiten' : 'Neue Organisation' }}</h2>
      <div class="form-field">
        <v-text-field v-model="form.name" label="Name" placeholder="Vendiqo GmbH" hide-details="auto" />
      </div>
      <div class="form-field">
        <v-text-field v-model="form.address" label="Adresse" placeholder="Musterstraße 12" hide-details="auto" />
      </div>
      <div class="field-row">
        <div class="form-field">
          <v-text-field v-model="form.zip" label="PLZ" placeholder="12345" hide-details="auto" />
        </div>
        <div class="form-field">
          <v-text-field v-model="form.city" label="Stadt" placeholder="Berlin" hide-details="auto" />
        </div>
      </div>
      <div class="form-field">
        <v-select v-model="form.country" :items="countryOptions" label="Land" placeholder="Land wählen" hide-details="auto" />
      </div>
      <div class="form-field">
        <label>Benutzer</label>
        <UserPicker v-model="form.userIdsArray" />
        <small>Feld anklicken für die Liste; tippen zum Filtern.</small>
      </div>

      <template v-if="editMode && orgApplianceLendings">
        <div class="org-lendings-toolbar">
          <v-btn color="primary" type="button" @click="lendingDialogVisible = true">
            Geräte ausleihen
          </v-btn>
        </div>
        <div class="org-lendings-block">
          <h3>Aktuell ausgeliehene Geräte</h3>
          <VqDataTable
            :headers="lendingHeaders"
            :items="orgApplianceLendings.current"
            item-value="lending_id"
            class="vq-data-table list-table nested-table"
            hide-default-footer
          >
            <template #item.appliance_name="{ item }">{{ item.appliance_name || '—' }}</template>
            <template #item.appliance_type="{ item }">{{ applianceTypeLabel(item.appliance_type) }}</template>
            <template #item.period="{ item }">
              {{ formatDeDate(item.start_date) }} – {{ formatDeDate(item.end_date) }}
            </template>
            <template #no-data>Keine aktiven Ausleihen.</template>
          </VqDataTable>
        </div>
        <div class="org-lendings-block">
          <h3>Geplante Ausleihen</h3>
          <VqDataTable
            :headers="plannedLendingHeaders"
            :items="orgApplianceLendings.planned"
            item-value="lending_id"
            class="vq-data-table list-table nested-table"
            hide-default-footer
          >
            <template #item.appliance_name="{ item }">{{ item.appliance_name || '—' }}</template>
            <template #item.appliance_type="{ item }">{{ applianceTypeLabel(item.appliance_type) }}</template>
            <template #item.period="{ item }">
              {{ formatDeDate(item.start_date) }} – {{ formatDeDate(item.end_date) }}
            </template>
            <template #item.actions="{ item }">
              <v-btn
                variant="outlined"
                size="small"
                type="button"
                :disabled="cancellingLendingId === item.lending_id"
                @click="cancelPlannedLendingRow(item)"
              >
                Stornieren
              </v-btn>
            </template>
            <template #no-data>Keine geplanten Ausleihen.</template>
          </VqDataTable>
        </div>
      </template>

      <ReceiptPrintingSection
        v-if="editMode && activeId"
        :api-base-path="`/organisations/${activeId}`"
        :entity-id="activeId"
        title="Beleg-Vorlagen (Organisation)"
        hint="Standard für neue Veranstaltungen dieser Organisation."
      />
      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
        <v-btn color="primary" :disabled="!form.name || !form.country" @click="saveOrganisation">
          Speichern
        </v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>

      <OrganisationLendingDialog
        v-if="editMode && activeId"
        v-model:visible="lendingDialogVisible"
        :organisation-id="activeId"
        :organisation-name="form.name"
        @completed="fetchOrgApplianceLendings(activeId)"
      />
    </template>

    <template #table>
      <ReceiptPrintingSection
        v-if="tenantHireCompanyId && canManageTenant"
        :api-base-path="`/hire-companies/${tenantHireCompanyId}`"
        :entity-id="tenantHireCompanyId"
        title="Beleg-Vorlagen (Verleiher)"
        hint="Gilt als Vorlage für neu angelegte Organisationen."
      />
      <div class="table-header">
        <h2>Alle Organisationen</h2>
        <span>{{ filteredOrganisations.length }} von {{ organisations.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            label="Suche"
            prepend-inner-icon="mdi-magnify"
            placeholder="Name, Adresse, Stadt oder Land suchen..."
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="countryFilter"
            :items="countryFilterOptions"
            item-title="label"
            item-value="value"
            label="Land"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="userFilter"
            :items="userFilterOptions"
            item-title="label"
            item-value="value"
            label="Benutzer"
            hide-details
            density="compact"
          />
        </div>
      </div>
      <VqDataTable
        :headers="tableHeaders"
        :items="paginatedOrganisations"
        item-value="id"
        class="vq-data-table list-table"
        hide-default-footer
        hover
        @click:row="(_, { item }) => editOrganisation(item)"
      >
        <template #item.location="{ item }">
          {{ item.address || '—' }}<span v-if="item.city"> · {{ item.city }}</span>
        </template>
        <template #item.user_ids="{ item }">{{ item.user_ids.length }}</template>
        <template #item.actions="{ item }">
          <v-btn color="error" variant="outlined" size="small" @click.stop="deleteOrganisation(item.id)">
            Löschen
          </v-btn>
        </template>
        <template #no-data>Keine Organisationen gefunden.</template>
      </VqDataTable>
      <div v-if="filteredOrganisations.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" density="compact" />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, onMounted, computed, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import ListDetailLayout from './ListDetailLayout.vue'
import OrganisationLendingDialog from './OrganisationLendingDialog.vue'
import ReceiptPrintingSection from './ReceiptPrintingSection.vue'
import UserPicker from './UserPicker.vue'
import { apiFetch } from '../api'
import { cancelPlannedLending } from '../utils/applianceLending'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'

const sessionContext = inject(SESSION_CONTEXT_KEY, null)
const tenantHireCompanyId = computed(() => sessionContext?.activeHireCompanyId?.value ?? null)
const canManageTenant = computed(() => Boolean(sessionContext?.canAccessTenantAdmin?.value))

const route = useRoute()
const {
  isCreateMode,
  editMode,
  showDetail,
  routeEntityId,
  goToList,
  goToCreate,
  goToDetail,
} = useListDetailRouting('organisations')

const organisations = ref([])
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const countryFilter = ref('')
const userFilter = ref('')
const currentPage = ref(1)
const pageSize = 20
const orgApplianceLendings = ref(null)
const lendingDialogVisible = ref(false)
const cancellingLendingId = ref(null)
const countryOptions = ['Deutschland', 'Österreich', 'Schweiz', 'Frankreich', 'Italien', 'Belgien', 'Niederlande']
const userFilterOptions = [
  { value: '', label: 'Alle' },
  { value: 'with-users', label: 'Mit Benutzern' },
  { value: 'without-users', label: 'Ohne Benutzer' },
]

const tableHeaders = [
  { title: 'ID', key: 'id' },
  { title: 'Name', key: 'name' },
  { title: 'Standort', key: 'location', sortable: false },
  { title: 'Land', key: 'country' },
  { title: 'Benutzer', key: 'user_ids', sortable: false },
  { title: 'Aktionen', key: 'actions', sortable: false, align: 'end' },
]

const lendingHeaders = [
  { title: 'ID', key: 'appliance_id' },
  { title: 'Gerät', key: 'appliance_name', sortable: false },
  { title: 'Typ', key: 'appliance_type', sortable: false },
  { title: 'Zeitraum', key: 'period', sortable: false },
]

const plannedLendingHeaders = [
  ...lendingHeaders,
  { title: 'Aktion', key: 'actions', sortable: false, align: 'end' },
]

const APPLIANCE_TYPE_LABELS = {
  server: 'Server',
  printer: 'Drucker',
  mobile: 'Mobil',
  tablet: 'Tablet',
  router: 'Router',
  ap: 'Access Point',
}

function applianceTypeLabel(type) {
  return APPLIANCE_TYPE_LABELS[type] || type
}

function formatDeDate(iso) {
  if (!iso) return '—'
  const [y, m, d] = String(iso).split('T')[0].split('-').map(Number)
  if (!y || !m || !d) return iso
  return new Date(y, m - 1, d).toLocaleDateString('de-DE')
}

const form = ref({
  name: '',
  address: '',
  zip: '',
  city: '',
  country: '',
  userIdsArray: [],
})

function matchesSearch(org, term) {
  if (!term) return true
  return [
    org.id,
    org.name,
    org.address,
    org.zip,
    org.city,
    org.country,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const availableCountries = computed(() => {
  return [...new Set(organisations.value.map((org) => org.country).filter(Boolean))].sort()
})

const countryFilterOptions = computed(() => [
  { value: '', label: 'Alle Länder' },
  ...availableCountries.value.map((country) => ({ value: country, label: country })),
])

const filteredOrganisations = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return organisations.value.filter((org) => {
    if (!matchesSearch(org, term)) return false
    if (countryFilter.value && org.country !== countryFilter.value) return false
    const userCount = Array.isArray(org.user_ids) ? org.user_ids.length : 0
    if (userFilter.value === 'with-users' && userCount === 0) return false
    if (userFilter.value === 'without-users' && userCount > 0) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredOrganisations.value.length / pageSize)))

const paginatedOrganisations = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredOrganisations.value.slice(start, start + pageSize)
})

const paginationLabel = computed(() => {
  if (!filteredOrganisations.value.length) return '0 Einträge'
  const start = (currentPage.value - 1) * pageSize + 1
  const end = Math.min(currentPage.value * pageSize, filteredOrganisations.value.length)
  return `${start}-${end} von ${filteredOrganisations.value.length}`
})

watch([searchQuery, countryFilter, userFilter], () => {
  currentPage.value = 1
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

function parseUserIds(value) {
  return value
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean)
    .map(Number)
    .filter((id) => !Number.isNaN(id))
}

async function fetchOrganisations() {
  try {
    const response = await apiFetch('/organisations/')
    organisations.value = await response.json()
  } catch (error) {
    message.value = 'Organisationen konnten nicht geladen werden.'
    messageType.value = 'error'
  }
}

async function fetchOrgApplianceLendings(orgId) {
  orgApplianceLendings.value = null
  try {
    const response = await apiFetch(`/organisations/${orgId}/appliance-lendings`)
    if (!response.ok) throw new Error(await response.text())
    orgApplianceLendings.value = await response.json()
  } catch {
    orgApplianceLendings.value = { current: [], planned: [], past: [] }
  }
}

async function cancelPlannedLendingRow(row) {
  if (!activeId.value || !row?.lending_id) return
  const label = row.appliance_name || `Gerät #${row.appliance_id}`
  if (!confirm(`Geplante Ausleihe für „${label}“ wirklich stornieren?`)) return
  cancellingLendingId.value = row.lending_id
  message.value = ''
  try {
    await cancelPlannedLending(activeId.value, row.lending_id)
    message.value = 'Geplante Ausleihe storniert.'
    messageType.value = 'success'
    await fetchOrgApplianceLendings(activeId.value)
  } catch (e) {
    message.value = e.message || 'Stornierung fehlgeschlagen.'
    messageType.value = 'error'
  } finally {
    cancellingLendingId.value = null
  }
}

const emptyOrgForm = () => ({
  name: '',
  address: '',
  zip: '',
  city: '',
  country: '',
  userIdsArray: [],
})

function applyOrganisationToForm(org) {
  form.value = {
    name: org.name,
    address: org.address || '',
    zip: org.zip || '',
    city: org.city || '',
    country: org.country,
    userIdsArray: org.user_ids ? org.user_ids.slice() : [],
  }
  message.value = ''
}

function clearFormState() {
  orgApplianceLendings.value = null
  lendingDialogVisible.value = false
  form.value = emptyOrgForm()
  message.value = ''
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
  let row = organisations.value.find((o) => Number(o.id) === Number(id))
  if (!row) {
    try {
      const response = await apiFetch(`/organisations/${id}`)
      if (!response.ok) throw new Error(await response.text())
      row = await response.json()
    } catch {
      message.value = 'Organisation nicht gefunden.'
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyOrganisationToForm(row)
  fetchOrgApplianceLendings(id)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function editOrganisation(org) {
  applyOrganisationToForm(org)
  goToDetail(org.id)
  fetchOrgApplianceLendings(org.id)
}

async function saveOrganisation() {
  const payload = {
    name: form.value.name,
    address: form.value.address || null,
    zip: form.value.zip || null,
    city: form.value.city || null,
    country: form.value.country,
    user_ids: Array.isArray(form.value.userIdsArray) ? form.value.userIdsArray : parseUserIds(form.value.userIds || ''),
  }

  try {
    const path = editMode.value ? `/organisations/${activeId.value}` : '/organisations/'
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
    const saved = await response.json()
    const wasEdit = editMode.value
    await fetchOrganisations()
    if (!wasEdit && sessionContext) {
      await sessionContext.reloadOrganisationsAndSelect(saved.id)
    }
    message.value = wasEdit ? 'Organisation aktualisiert.' : 'Organisation erstellt.'
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = 'Fehler beim Speichern der Organisation.'
    messageType.value = 'error'
  }
}

async function deleteOrganisation(id) {
  if (!confirm('Organisation wirklich löschen?')) {
    return
  }
  try {
    const response = await apiFetch(`/organisations/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error(await response.text())
    }
    await fetchOrganisations()
    message.value = 'Organisation gelöscht.'
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = 'Organisation konnte nicht gelöscht werden.'
    messageType.value = 'error'
  }
}

onMounted(fetchOrganisations)
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

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

small {
  color: rgba(var(--v-theme-on-surface), 0.65);
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

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.org-lendings-toolbar {
  margin-top: 1.5rem;
}

.org-lendings-block {
  margin-top: 1rem;
}

.org-lendings-block h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  color: rgb(var(--v-theme-on-surface));
}

.nested-table {
  margin-bottom: 0.5rem;
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
