<template>
  <ListDetailLayout
    :title="$t('users.title')"
    :subtitle="$t('users.subtitle')"
    :createLabel="$t('users.createLabel')"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #header-actions>
      <HelpLink slug="user-management" variant="icon" />
    </template>
    <template #detail>
      <h2>{{ editMode ? $t('users.editTitle') : $t('users.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveUser">
      <div class="form-field">
        <v-text-field
          v-model="form.name"
          :label="$t('common.name')"
          :placeholder="$t('users.namePlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>
      <div class="form-field">
        <v-text-field
          v-model="form.email"
          :label="$t('common.email')"
          type="email"
          :placeholder="$t('users.emailPlaceholder')"
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
          :label="$t('common.role')"
          hide-details="auto"
        />
      </div>
      <div class="form-field" v-if="!editMode">
        <v-text-field
          v-model="form.password"
          :type="showPassword ? 'text' : 'password'"
          :label="$t('common.password')"
          :placeholder="$t('users.passwordPlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
          :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
          @click:append-inner="showPassword = !showPassword"
        />
      </div>
      <div class="form-field">
        <label>{{ $t('common.organisations') }}</label>
        <OrganisationPicker v-model="form.organisationIdsArray" />
        <small>{{ $t('users.organisationsHint') }}</small>
      </div>
      <div v-if="hasOrganisations" class="form-field">
        <v-text-field
          v-model="form.eventAdminPin"
          :label="$t('users.eventAdminPin')"
          :placeholder="$t('common.optional')"
          maxlength="6"
          inputmode="numeric"
          :disabled="form.clearEventAdminPin"
          hide-details="auto"
        />
        <small>{{ $t('users.eventAdminPinHint') }}</small>
        <v-checkbox
          v-if="editMode && form.hasEventAdminPin"
          v-model="form.clearEventAdminPin"
          :label="$t('users.clearEventAdminPin')"
          hide-details
          density="compact"
          class="mt-2"
        />
      </div>
      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
        <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <div class="table-header">
        <h2>{{ $t('users.allTitle') }}</h2>
        <span>{{ $t('common.entriesCount', { filtered: filteredUsers.length, total: users.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            :label="$t('common.search')"
            prepend-inner-icon="mdi-magnify"
            :placeholder="$t('users.searchPlaceholder')"
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
            :label="$t('common.role')"
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
            :label="$t('common.organisation')"
            hide-details
            density="compact"
          />
        </div>
      </div>
      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredUsers"
        :items-per-page="pageSize"
        item-value="id"
        class="vq-data-table list-table"
        hover
        @click:row="(_, { item }) => editUser(item)"
      >
        <template #item.role="{ item }">{{ roleLabel(item.role) }}</template>
        <template #item.has_event_admin_pin="{ item }">
          {{ item.has_event_admin_pin ? $t('common.yes') : $t('common.no') }}
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
            {{ $t('common.delete') }}
          </v-btn>
        </template>
        <template #no-data>{{ $t('users.noData') }}</template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import VqDataTable from './VqDataTable.vue'

// isAdmin prop = platform administrator (from App.vue)
import ListDetailLayout from './ListDetailLayout.vue'
import HelpLink from './HelpLink.vue'
import OrganisationPicker from './OrganisationPicker.vue'
import { apiFetch } from '../api'
import { rules, validateForm } from '../utils/formRules.js'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'

const { t } = useI18n()

const props = defineProps({
  isAdmin: { type: Boolean, default: false },
  isTenantAdmin: { type: Boolean, default: false },
  isOrganisationAdmin: { type: Boolean, default: false },
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
const showPassword = ref(false)

const tableHeaders = computed(() => [
  { title: t('common.id'), key: 'id' },
  { title: t('common.name'), key: 'name' },
  { title: t('common.email'), key: 'email' },
  { title: t('common.role'), key: 'role', sortable: false },
  { title: t('users.piCode'), key: 'has_event_admin_pin', sortable: false },
  { title: t('common.organisations'), key: 'organisations', sortable: false },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

const roleFilterOptions = computed(() => [
  { value: '', label: t('users.allRoles') },
  { value: 'tenant_admin', label: t('users.roleTenantAdmin') },
  { value: 'organisation_admin', label: t('users.roleOrganisationAdmin') },
  { value: 'member', label: t('users.roleMember') },
])

const roleOptions = computed(() => {
  if (props.isOrganisationAdmin && !props.isTenantAdmin && !props.isAdmin) {
    return [
      { value: 'member', label: t('users.roleMemberSingular') },
      { value: 'organisation_admin', label: t('users.roleOrganisationAdminSingular') },
    ]
  }
  const opts = [
    { value: 'member', label: t('users.roleMemberSingular') },
    { value: 'organisation_admin', label: t('users.roleOrganisationAdminSingular') },
    { value: 'tenant_admin', label: t('users.roleTenantAdminSingular') },
  ]
  if (props.isAdmin) {
    opts.push({ value: 'platform_admin', label: t('users.rolePlatformAdmin') })
  }
  return opts
})

function roleLabel(role) {
  if (role === 'platform_admin') return t('users.rolePlatformAdmin')
  if (role === 'tenant_admin') return t('users.roleTenantAdminSingular')
  if (role === 'organisation_admin') return t('users.roleOrganisationAdminSingular')
  return t('users.roleMemberSingular')
}

const organisationFilterOptions = computed(() => [
  { value: '', label: t('common.all') },
  { value: 'with-orgs', label: t('users.withOrganisations') },
  { value: 'without-orgs', label: t('users.withoutOrganisation') },
])

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
  return t('common.emDash')
}

function organisationsTitle(u) {
  const text = formatOrgs(u)
  return text === t('common.emDash') ? '' : text
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

const { currentPage, pageSize } = useClientPagination(filteredUsers, {
  resetOn: [searchQuery, roleFilter, organisationFilter],
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
    message.value = t('users.loadError')
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
    message.value = t('users.notFound')
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
    message.value = wasEdit ? t('users.updated') : t('users.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('users.saveError')
    messageType.value = 'error'
  }
}

async function deleteUser(id) {
  if (!confirm(t('users.deleteConfirm'))) {
    return
  }
  try {
    const resp = await apiFetch(`/users/${id}`, {
      method: 'DELETE',
    })
    if (!resp.ok) throw new Error(await resp.text())
    await fetchUsers()
    message.value = t('users.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('users.deleteError')
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

.table-header span {
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
