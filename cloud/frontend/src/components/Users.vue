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
      <p class="form-required-legend"><span class="vq-asterisk">*</span> Pflichtfeld</p>

      <v-form ref="formRef" @submit.prevent="saveUser">
      <div class="form-field">
        <v-text-field
          v-model="form.name"
          label="Name"
          placeholder="Max Mustermann"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="form-field">
        <v-text-field
          v-model="form.email"
          label="Email"
          type="email"
          placeholder="max@example.com"
          hide-details="auto"
          required
          :rules="[rules.required, rules.email]"
        />
      </div>
      <div class="form-field">
        <v-select
          v-model="form.role"
          :items="roleOptions"
          item-title="label"
          item-value="value"
          label="Rolle"
          hide-details="auto"
        />
      </div>
      <div class="form-field" v-if="!editMode">
        <v-text-field
          v-model="form.password"
          :type="showPassword ? 'text' : 'password'"
          label="Passwort"
          placeholder="Passwort setzen"
          hide-details="auto"
          required
          :rules="[rules.required]"
          :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
          @click:append-inner="showPassword = !showPassword"
        />
      </div>
      <div class="form-field">
        <label>Organisationen</label>
        <OrganisationPicker v-model="form.organisationIdsArray" />
        <small>Keine, eine oder mehrere Organisationen zuordnen.</small>
      </div>
      <div v-if="hasOrganisations" class="form-field">
        <v-text-field
          v-model="form.eventAdminPin"
          label="Pi Admin-Code (6 Ziffern)"
          placeholder="Optional"
          maxlength="6"
          inputmode="numeric"
          :disabled="form.clearEventAdminPin"
          hide-details="auto"
        />
        <small>Freischaltung der Admin-Funktionen auf dem Pi (Sync, Konfiguration).</small>
        <v-checkbox
          v-if="editMode && form.hasEventAdminPin"
          v-model="form.clearEventAdminPin"
          label="Pi Admin-Code entfernen"
          hide-details
          density="compact"
          class="mt-2"
        />
      </div>
      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
        <v-btn color="primary" type="submit">Speichern</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <div class="table-header">
        <h2>Alle Benutzer</h2>
        <span>{{ filteredUsers.length }} von {{ users.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            label="Suche"
            prepend-inner-icon="mdi-magnify"
            placeholder="Name, E-Mail oder Organisation suchen..."
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="roleFilter"
            :items="roleFilterOptions"
            item-title="label"
            item-value="value"
            label="Rolle"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="organisationFilter"
            :items="organisationFilterOptions"
            item-title="label"
            item-value="value"
            label="Organisation"
            hide-details
            density="compact"
          />
        </div>
      </div>
      <VqDataTable
        :headers="tableHeaders"
        :items="paginatedUsers"
        item-value="id"
        class="vq-data-table list-table"
        hide-default-footer
        hover
        @click:row="(_, { item }) => editUser(item)"
      >
        <template #item.role="{ item }">{{ roleLabel(item.role) }}</template>
        <template #item.has_event_admin_pin="{ item }">
          {{ item.has_event_admin_pin ? 'Ja' : 'Nein' }}
        </template>
        <template #item.organisations="{ item }">
          <span class="cell-orgs" :title="organisationsTitle(item)">{{ formatOrgs(item) }}</span>
        </template>
        <template #item.actions="{ item }">
          <v-btn
            v-if="currentUserId === null || item.id !== currentUserId"
            color="error"
            variant="outlined"
            size="small"
            @click.stop="deleteUser(item.id)"
          >
            Löschen
          </v-btn>
        </template>
        <template #no-data>Keine Benutzer gefunden.</template>
      </VqDataTable>
      <div v-if="filteredUsers.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" density="compact" />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import VqDataTable from './VqDataTable.vue'

// isAdmin prop = platform administrator (from App.vue)
import ListDetailLayout from './ListDetailLayout.vue'
import OrganisationPicker from './OrganisationPicker.vue'
import { apiFetch } from '../api'
import { rules, validateForm } from '../utils/formRules.js'
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
const showPassword = ref(false)

const tableHeaders = [
  { title: 'ID', key: 'id' },
  { title: 'Name', key: 'name' },
  { title: 'Email', key: 'email' },
  { title: 'Rolle', key: 'role', sortable: false },
  { title: 'Pi-Code', key: 'has_event_admin_pin', sortable: false },
  { title: 'Organisationen', key: 'organisations', sortable: false },
  { title: 'Aktionen', key: 'actions', sortable: false, align: 'end' },
]
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
const formRef = ref(null)

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
  if (!(await validateForm(formRef))) return
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
  color: rgb(var(--v-theme-on-surface));
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
