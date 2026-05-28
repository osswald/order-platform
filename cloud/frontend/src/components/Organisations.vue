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
        <label>Name</label>
        <InputText v-model="form.name" placeholder="Vendiqo GmbH" />
      </div>
      <div class="form-field">
        <label>Adresse</label>
        <InputText v-model="form.address" placeholder="Musterstraße 12" />
      </div>
      <div class="field-row">
        <div class="form-field">
          <label>PLZ</label>
          <InputText v-model="form.zip" placeholder="12345" />
        </div>
        <div class="form-field">
          <label>Stadt</label>
          <InputText v-model="form.city" placeholder="Berlin" />
        </div>
      </div>
      <div class="form-field">
        <label>Land</label>
        <Select v-model="form.country" :options="countryOptions" placeholder="Land wählen" />
      </div>
      <div class="form-field">
        <label>Benutzer</label>
        <UserPicker v-model="form.userIdsArray" />
        <small>Feld anklicken für die Liste; tippen zum Filtern.</small>
      </div>

      <template v-if="editMode && orgApplianceLendings">
        <div class="org-lendings-toolbar">
          <Button
            label="Geräte ausleihen"
            class="primary-button"
            type="button"
            @click="lendingDialogVisible = true"
          />
        </div>
        <div class="org-lendings-block">
          <h3>Aktuell ausgeliehene Geräte</h3>
          <DataTable
            :value="orgApplianceLendings.current"
            dataKey="lending_id"
            class="list-table nested-table"
            responsiveLayout="stack"
            breakpoint="768px"
          >
            <template #empty>Keine aktiven Ausleihen.</template>
            <Column field="appliance_id" header="ID" />
            <Column header="Gerät">
              <template #body="{ data }">{{ data.appliance_name || '—' }}</template>
            </Column>
            <Column header="Typ">
              <template #body="{ data }">{{ applianceTypeLabel(data.appliance_type) }}</template>
            </Column>
            <Column header="Zeitraum">
              <template #body="{ data }">{{ formatDeDate(data.start_date) }} – {{ formatDeDate(data.end_date) }}</template>
            </Column>
          </DataTable>
        </div>
        <div class="org-lendings-block">
          <h3>Geplante Ausleihen</h3>
          <DataTable
            :value="orgApplianceLendings.planned"
            dataKey="lending_id"
            class="list-table nested-table"
            responsiveLayout="stack"
            breakpoint="768px"
          >
            <template #empty>Keine geplanten Ausleihen.</template>
            <Column field="appliance_id" header="ID" />
            <Column header="Gerät">
              <template #body="{ data }">{{ data.appliance_name || '—' }}</template>
            </Column>
            <Column header="Typ">
              <template #body="{ data }">{{ applianceTypeLabel(data.appliance_type) }}</template>
            </Column>
            <Column header="Zeitraum">
              <template #body="{ data }">{{ formatDeDate(data.start_date) }} – {{ formatDeDate(data.end_date) }}</template>
            </Column>
            <Column header="Aktion">
              <template #body="{ data }">
                <Button
                  label="Stornieren"
                  class="secondary-button"
                  type="button"
                  :disabled="cancellingLendingId === data.lending_id"
                  @click="cancelPlannedLendingRow(data)"
                />
              </template>
            </Column>
          </DataTable>
        </div>
      </template>

      <div class="actions">
        <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
        <Button label="Speichern" class="primary-button" :disabled="!form.name || !form.country" @click="saveOrganisation" />
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
      <div class="table-header">
        <h2>Alle Organisationen</h2>
        <span>{{ filteredOrganisations.length }} von {{ organisations.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="searchQuery" placeholder="Name, Adresse, Stadt oder Land suchen..." />
          </IconField>
        </div>
        <div class="filter-field">
          <label>Land</label>
          <Select v-model="countryFilter" :options="countryFilterOptions" optionLabel="label" optionValue="value" placeholder="Alle Länder" />
        </div>
        <div class="filter-field">
          <label>Benutzer</label>
          <Select v-model="userFilter" :options="userFilterOptions" optionLabel="label" optionValue="value" placeholder="Alle" />
        </div>
      </div>
      <DataTable
        :value="paginatedOrganisations"
        dataKey="id"
        responsiveLayout="stack"
        breakpoint="768px"
        class="list-table"
        @row-click="editOrganisation($event.data)"
      >
        <template #empty>Keine Organisationen gefunden.</template>
        <Column field="id" header="ID" />
        <Column field="name" header="Name" />
        <Column header="Standort">
          <template #body="{ data }">
            {{ data.address || '—' }}<span v-if="data.city"> · {{ data.city }}</span>
          </template>
        </Column>
        <Column field="country" header="Land" />
        <Column header="Benutzer">
          <template #body="{ data }">{{ data.user_ids.length }}</template>
        </Column>
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button label="Löschen" class="danger" @click.stop="deleteOrganisation(data.id)" />
          </template>
        </Column>
      </DataTable>
      <div v-if="filteredOrganisations.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <Paginator
          :first="(currentPage - 1) * pageSize"
          :rows="pageSize"
          :totalRecords="filteredOrganisations.length"
          @page="currentPage = $event.page + 1"
        />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, onMounted, computed, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'
import ListDetailLayout from './ListDetailLayout.vue'
import OrganisationLendingDialog from './OrganisationLendingDialog.vue'
import UserPicker from './UserPicker.vue'
import { apiFetch } from '../api'
import { cancelPlannedLending } from '../utils/applianceLending'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { SESSION_CONTEXT_KEY } from '../sessionContext'

const sessionContext = inject(SESSION_CONTEXT_KEY, null)

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
:deep(.p-select) {
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
  color: var(--p-text-color);
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
