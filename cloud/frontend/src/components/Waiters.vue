<template>
  <ListDetailLayout
    title="Kellner"
    subtitle="Kellner pro Organisation verwalten."
    createLabel="Neuer Kellner"
    :showCreate="canCreateWaiters"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? 'Kellner bearbeiten' : 'Neuer Kellner' }}</h2>

      <div class="form-field">
        <label>Name</label>
        <InputText v-model="form.name" placeholder="Max Mustermann" />
      </div>

      <div class="form-field">
        <label>PIN</label>
        <InputText v-model="form.pin" placeholder="0000" />
        <small>Standard-PIN ist 0000.</small>
      </div>

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
      </div>

      <div class="actions">
        <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
        <Button label="Speichern" class="primary-button" :disabled="!canSave" @click="saveWaiter" />
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <div class="table-header">
        <h2>Alle Kellner</h2>
        <span>{{ filteredWaiters.length }} von {{ waitersInActiveOrganisation.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="searchQuery" placeholder="Name, PIN oder Organisation suchen..." />
          </IconField>
        </div>
      </div>

      <DataTable
        :value="paginatedWaiters"
        dataKey="id"
        responsiveLayout="scroll"
        class="list-table"
        @row-click="editWaiter($event.data)"
      >
        <template #empty>Keine Kellner gefunden.</template>
        <Column field="id" header="ID" />
        <Column field="name" header="Name" />
        <Column field="pin" header="PIN" />
        <Column field="organisation_name" header="Organisation" />
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button label="Löschen" class="danger" @click.stop="deleteWaiter(data.id)" />
          </template>
        </Column>
      </DataTable>

      <div v-if="filteredWaiters.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <Paginator
          :first="(currentPage - 1) * pageSize"
          :rows="pageSize"
          :totalRecords="filteredWaiters.length"
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
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import Select from 'primevue/select'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiFetch } from '../api'
import { matchesActiveOrganisation } from '../orgScope'

const props = defineProps({
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

const waiters = ref([])
const organisations = ref([])
const showDetail = ref(false)
const editMode = ref(false)
const activeId = ref(null)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = 20

const emptyForm = () => ({
  name: '',
  pin: '0000',
  organisationId: null,
})

const form = ref(emptyForm())

const organisationOptions = computed(() =>
  organisations.value.map((org) => ({ value: org.id, label: org.name }))
)

const canCreateWaiters = computed(() => organisationOptions.value.length > 0)

const canSave = computed(() => !!(form.value.name && form.value.pin && form.value.organisationId))

function matchesSearch(waiter, term) {
  if (!term) return true
  return [
    waiter.id,
    waiter.name,
    waiter.pin,
    waiter.organisation_name,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredWaiters = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return waiters.value.filter((waiter) => {
    if (!matchesSearch(waiter, term)) return false
    if (!matchesActiveOrganisation(props.activeOrganisationId, waiter.organisation_id)) return false
    return true
  })
})

const waitersInActiveOrganisation = computed(() =>
  waiters.value.filter((waiter) =>
    matchesActiveOrganisation(props.activeOrganisationId, waiter.organisation_id)
  )
)

const totalPages = computed(() => Math.max(1, Math.ceil(filteredWaiters.value.length / pageSize)))

const paginatedWaiters = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredWaiters.value.slice(start, start + pageSize)
})

const paginationLabel = computed(() => {
  if (!filteredWaiters.value.length) return '0 Einträge'
  const start = (currentPage.value - 1) * pageSize + 1
  const end = Math.min(currentPage.value * pageSize, filteredWaiters.value.length)
  return `${start}-${end} von ${filteredWaiters.value.length}`
})

watch([searchQuery, () => props.activeOrganisationId], () => {
  currentPage.value = 1
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

async function fetchWaiters() {
  try {
    const response = await apiFetch('/waiters/')
    if (!response.ok) throw new Error(await response.text())
    waiters.value = await response.json()
  } catch (error) {
    message.value = 'Kellner konnten nicht geladen werden.'
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

function resetForm() {
  editMode.value = false
  activeId.value = null
  showDetail.value = false
  form.value = emptyForm()
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

function editWaiter(waiter) {
  showDetail.value = true
  editMode.value = true
  activeId.value = waiter.id
  form.value = {
    name: waiter.name || '',
    pin: waiter.pin || '0000',
    organisationId: waiter.organisation_id || null,
  }
  message.value = ''
}

async function saveWaiter() {
  const payload = {
    name: form.value.name,
    pin: form.value.pin || '0000',
    organisation_id: form.value.organisationId,
  }

  try {
    const path = editMode.value ? `/waiters/${activeId.value}` : '/waiters/'
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
    await fetchWaiters()
    resetForm()
    message.value = wasEdit ? 'Kellner aktualisiert.' : 'Kellner erstellt.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Fehler beim Speichern des Kellners.'
    messageType.value = 'error'
  }
}

async function deleteWaiter(id) {
  if (!confirm('Kellner wirklich löschen?')) return
  try {
    const response = await apiFetch(`/waiters/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error(await response.text())
    await fetchWaiters()
    message.value = 'Kellner gelöscht.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Kellner konnte nicht gelöscht werden.'
    messageType.value = 'error'
  }
}

onMounted(async () => {
  await fetchOrganisations()
  await fetchWaiters()
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

small,
.table-header span,
.pagination {
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
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

.list-controls {
  display: grid;
  grid-template-columns: minmax(240px, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}

.search-field {
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

@media (max-width: 700px) {
  .pagination {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
