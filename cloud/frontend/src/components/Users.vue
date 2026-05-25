<template>
  <ListDetailLayout
    title="Benutzer"
    subtitle="Benutzer verwalten und Berechtigungen setzen."
    createLabel="Neuen Benutzer"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? 'Benutzer bearbeiten' : 'Neuen Benutzer' }}</h2>
      <div class="form-field">
        <label>Name</label>
        <InputText v-model="form.name" placeholder="Max Mustermann" />
      </div>
      <div class="form-field">
        <label>Email</label>
        <InputText v-model="form.email" placeholder="max@example.com" />
      </div>
      <div class="form-field">
        <label>Rolle</label>
        <Select v-model="form.role" :options="roleOptions" optionLabel="label" optionValue="value" />
      </div>
      <div class="form-field" v-if="!editMode">
        <label>Passwort</label>
        <Password v-model="form.password" placeholder="Passwort setzen" :feedback="false" toggleMask />
      </div>
      <div class="form-field">
        <label>Organisationen</label>
        <OrganisationPicker v-model="form.organisationIdsArray" />
        <small>Keine, eine oder mehrere Organisationen zuordnen.</small>
      </div>
      <div v-if="hasOrganisations" class="form-field">
        <label>Pi Admin-Code (6 Ziffern)</label>
        <InputMask
          v-model="form.eventAdminPin"
          mask="999999"
          slotChar=""
          placeholder="Optional"
          :disabled="form.clearEventAdminPin"
        />
        <small>Freischaltung der Admin-Funktionen auf dem Pi (Sync, Konfiguration).</small>
        <div v-if="editMode && form.hasEventAdminPin" class="checkbox-field" style="margin-top: 0.5rem">
          <Checkbox v-model="form.clearEventAdminPin" binary inputId="clear-pin" />
          <label for="clear-pin">Pi Admin-Code entfernen</label>
        </div>
      </div>
      <div class="actions">
        <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
        <Button
          label="Speichern"
          class="primary-button"
          :disabled="!form.name || !form.email || (!editMode && !form.password)"
          @click="saveUser"
        />
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <div class="table-header">
        <h2>Alle Benutzer</h2>
        <span>{{ filteredUsers.length }} von {{ users.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="searchQuery" placeholder="Name, E-Mail oder Organisation suchen..." />
          </IconField>
        </div>
        <div class="filter-field">
          <label>Rolle</label>
          <Select v-model="roleFilter" :options="roleFilterOptions" optionLabel="label" optionValue="value" placeholder="Alle Rollen" />
        </div>
        <div class="filter-field">
          <label>Organisation</label>
          <Select v-model="organisationFilter" :options="organisationFilterOptions" optionLabel="label" optionValue="value" placeholder="Alle" />
        </div>
      </div>
      <DataTable
        :value="paginatedUsers"
        dataKey="id"
        responsiveLayout="scroll"
        class="list-table"
        @row-click="editUser($event.data)"
      >
        <template #empty>Keine Benutzer gefunden.</template>
        <Column field="id" header="ID" />
        <Column field="name" header="Name" />
        <Column field="email" header="Email" />
        <Column header="Rolle">
          <template #body="{ data }">{{ roleLabel(data.role) }}</template>
        </Column>
        <Column header="Pi-Code">
          <template #body="{ data }">{{ data.has_event_admin_pin ? 'Ja' : 'Nein' }}</template>
        </Column>
        <Column header="Organisationen">
          <template #body="{ data }">
            <span class="cell-orgs" :title="organisationsTitle(data)">{{ formatOrgs(data) }}</span>
          </template>
        </Column>
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button
              v-if="currentUserId === null || data.id !== currentUserId"
              label="Löschen"
              class="danger"
              @click.stop="deleteUser(data.id)"
            />
          </template>
        </Column>
      </DataTable>
      <div v-if="filteredUsers.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <Paginator
          :first="(currentPage - 1) * pageSize"
          :rows="pageSize"
          :totalRecords="filteredUsers.length"
          @page="currentPage = $event.page + 1"
        />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'

// isAdmin prop = platform administrator (from App.vue)
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputMask from 'primevue/inputmask'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Password from 'primevue/password'
import Select from 'primevue/select'
import ListDetailLayout from './ListDetailLayout.vue'
import OrganisationPicker from './OrganisationPicker.vue'
import { apiFetch } from '../api'
import { useListDetailRouting } from '../composables/useListDetailRouting'

const props = defineProps({
  isAdmin: { type: Boolean, default: false },
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
} = useListDetailRouting('users')

const users = ref([])
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const roleFilter = ref('')
const organisationFilter = ref('')
const currentPage = ref(1)
const pageSize = 20
const roleFilterOptions = [
  { value: '', label: 'Alle Rollen' },
  { value: 'org_admin', label: 'Organisations-Admins' },
  { value: 'member', label: 'Mitglieder' },
]

const roleOptions = computed(() => {
  const opts = [
    { value: 'member', label: 'Mitglied' },
    { value: 'org_admin', label: 'Organisations-Admin' },
  ]
  if (props.isAdmin) {
    opts.push({ value: 'platform_admin', label: 'Plattform-Admin' })
  }
  return opts
})

function roleLabel(role) {
  if (role === 'platform_admin') return 'Plattform-Admin'
  if (role === 'org_admin') return 'Organisations-Admin'
  return 'Mitglied'
}
const organisationFilterOptions = [
  { value: '', label: 'Alle' },
  { value: 'with-orgs', label: 'Mit Organisationen' },
  { value: 'without-orgs', label: 'Ohne Organisation' },
]

const form = ref({
  name: '',
  email: '',
  role: 'member',
  password: '',
  organisationIdsArray: [],
  eventAdminPin: '',
  hasEventAdminPin: false,
  clearEventAdminPin: false,
})

const hasOrganisations = computed(() => (form.value.organisationIdsArray?.length || 0) > 0)

const currentUserId = computed(() => {
  const raw = localStorage.getItem('user_id')
  if (raw == null || raw === '') return null
  const n = Number(raw)
  return Number.isNaN(n) ? null : n
})

function formatOrgs(u) {
  if (u.organisations?.length) {
    return u.organisations.map((o) => o.name).join(', ')
  }
  if (u.organisation_ids?.length) {
    return u.organisation_ids.map((id) => `#${id}`).join(', ')
  }
  return '—'
}

function organisationsTitle(u) {
  const t = formatOrgs(u)
  return t === '—' ? '' : t
}

function organisationCount(u) {
  if (Array.isArray(u.organisations)) return u.organisations.length
  if (Array.isArray(u.organisation_ids)) return u.organisation_ids.length
  return 0
}

function matchesSearch(u, term) {
  if (!term) return true
  return [
    u.id,
    u.name,
    u.email,
    formatOrgs(u),
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredUsers = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return users.value.filter((u) => {
    if (!matchesSearch(u, term)) return false
    if (roleFilter.value && u.role !== roleFilter.value) return false
    const orgCount = organisationCount(u)
    if (organisationFilter.value === 'with-orgs' && orgCount === 0) return false
    if (organisationFilter.value === 'without-orgs' && orgCount > 0) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredUsers.value.length / pageSize)))

const paginatedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredUsers.value.slice(start, start + pageSize)
})

const paginationLabel = computed(() => {
  if (!filteredUsers.value.length) return '0 Einträge'
  const start = (currentPage.value - 1) * pageSize + 1
  const end = Math.min(currentPage.value * pageSize, filteredUsers.value.length)
  return `${start}-${end} von ${filteredUsers.value.length}`
})

watch([searchQuery, roleFilter, organisationFilter], () => {
  currentPage.value = 1
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

async function fetchUsers() {
  try {
    const resp = await apiFetch('/users/')
    if (!resp.ok) {
      const text = await resp.text()
      throw new Error(text || resp.statusText)
    }
    users.value = await resp.json()
  } catch (e) {
    message.value = 'Benutzer konnten nicht geladen werden.'
    messageType.value = 'error'
  }
}

const emptyUserForm = () => ({
  name: '',
  email: '',
  role: 'member',
  password: '',
  organisationIdsArray: [],
  eventAdminPin: '',
  hasEventAdminPin: false,
  clearEventAdminPin: false,
})

function applyUserToForm(u) {
  form.value = {
    name: u.name || '',
    email: u.email || '',
    role: u.role || (u.is_admin ? 'platform_admin' : 'member'),
    password: '',
    organisationIdsArray: Array.isArray(u.organisation_ids) ? u.organisation_ids.slice() : [],
    eventAdminPin: '',
    hasEventAdminPin: !!u.has_event_admin_pin,
    clearEventAdminPin: false,
  }
  message.value = ''
}

function clearFormState() {
  form.value = emptyUserForm()
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
  const row = users.value.find((u) => Number(u.id) === Number(id))
  if (!row) {
    message.value = 'Benutzer nicht gefunden.'
    messageType.value = 'error'
    goToList()
    return
  }
  applyUserToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function editUser(u) {
  applyUserToForm(u)
  goToDetail(u.id)
}

async function saveUser() {
  const payload = {
    name: form.value.name,
    email: form.value.email,
    role: form.value.role,
    organisation_ids: Array.isArray(form.value.organisationIdsArray)
      ? form.value.organisationIdsArray.map(Number)
      : [],
  }
  if (!editMode.value) payload.password = form.value.password
  if (hasOrganisations.value) {
    if (editMode.value && form.value.clearEventAdminPin) {
      payload.event_admin_pin = ''
    } else if (form.value.eventAdminPin && String(form.value.eventAdminPin).length === 6) {
      payload.event_admin_pin = String(form.value.eventAdminPin)
    }
  }
  try {
    const path = editMode.value ? `/users/${activeId.value}` : '/users/'
    const method = editMode.value ? 'PUT' : 'POST'
    const resp = await apiFetch(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    if (!resp.ok) throw new Error(await resp.text())
    const wasEdit = editMode.value
    await fetchUsers()
    message.value = wasEdit ? 'Benutzer aktualisiert.' : 'Benutzer erstellt.'
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = 'Fehler beim Speichern des Benutzers.'
    messageType.value = 'error'
  }
}

async function deleteUser(id) {
  if (!confirm('Benutzer wirklich löschen?')) {
    return
  }
  try {
    const resp = await apiFetch(`/users/${id}`, {
      method: 'DELETE',
    })
    if (!resp.ok) throw new Error(await resp.text())
    await fetchUsers()
    message.value = 'Benutzer gelöscht.'
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = 'Benutzer konnte nicht gelöscht werden.'
    messageType.value = 'error'
  }
}

onMounted(fetchUsers)
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

.checkbox-field {
  align-items: flex-start;
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
:deep(.p-password) {
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

.cell-orgs {
  display: inline-block;
  max-width: 16rem;
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
