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
        <v-text-field v-model="form.name" placeholder="Max Mustermann" hide-details="auto" />
      </div>

      <div class="form-field">
        <label>PIN</label>
        <v-text-field v-model="form.pin" placeholder="0000" hide-details="auto" />
        <small>Standard-PIN ist 0000.</small>
      </div>

      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
        <v-btn color="primary" :disabled="!canSave" @click="saveWaiter">Speichern</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        Bitte wählen Sie links eine Organisation.
      </p>
      <div class="table-header">
        <h2>Alle Kellner</h2>
        <span>{{ filteredWaiters.length }} von {{ waitersInActiveOrganisation.length }} Einträge</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <v-text-field
            v-model="searchQuery"
            placeholder="Name, PIN oder Organisation suchen..."
            prepend-inner-icon="mdi-magnify"
            hide-details="auto"
          />
        </div>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredWaiters"
        :items-per-page="pageSize"
        item-value="id"
        hover
        no-data-text="Keine Kellner gefunden."
        class="vq-data-table list-table"
        @click:row="(_e, { item }) => editWaiter(item)"
      >
        <template #item.actions="{ item }">
          <v-btn color="error" variant="text" @click.stop="deleteWaiter(item.id)">Löschen</v-btn>
        </template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiFetch } from '../api'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { matchesActiveOrganisation } from '../utils/orgScope'
import VqDataTable from './VqDataTable.vue'

const props = defineProps({
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
} = useListDetailRouting('waiters')

const tableHeaders = [
  { title: 'ID', key: 'id' },
  { title: 'Name', key: 'name' },
  { title: 'PIN', key: 'pin' },
  { title: 'Organisation', key: 'organisation_name' },
  { title: 'Aktionen', key: 'actions', sortable: false, align: 'end' },
]

const waiters = ref([])
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = 20

const emptyForm = () => ({
  name: '',
  pin: '0000',
})

const form = ref(emptyForm())

const canCreateWaiters = computed(() => props.activeOrganisationId != null)

const canSave = computed(
  () => !!(props.activeOrganisationId != null && form.value.name && form.value.pin),
)

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
    matchesActiveOrganisation(props.activeOrganisationId, waiter.organisation_id),
  ),
)

watch([searchQuery, () => props.activeOrganisationId], () => {
  currentPage.value = 1
})

watch(
  () => props.activeOrganisationId,
  () => {
    if (showDetail.value) goToList()
  },
)

async function fetchWaiters() {
  try {
    const response = await apiFetch('/waiters/')
    if (!response.ok) throw new Error(await response.text())
    waiters.value = await response.json()
  } catch {
    message.value = 'Kellner konnten nicht geladen werden.'
    messageType.value = 'error'
  }
}

function applyWaiterToForm(waiter) {
  form.value = {
    name: waiter.name || '',
    pin: waiter.pin || '0000',
  }
  message.value = ''
}

function clearFormState() {
  form.value = emptyForm()
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
  let row = waiters.value.find((w) => Number(w.id) === Number(id))
  if (!row) {
    try {
      const response = await apiFetch(`/waiters/${id}`)
      if (!response.ok) throw new Error(await response.text())
      row = await response.json()
    } catch {
      message.value = 'Kellner nicht gefunden.'
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyWaiterToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function editWaiter(waiter) {
  applyWaiterToForm(waiter)
  goToDetail(waiter.id)
}

async function saveWaiter() {
  const payload = {
    name: form.value.name,
    pin: form.value.pin || '0000',
  }
  if (!editMode.value) {
    payload.organisation_id = props.activeOrganisationId
  }

  try {
    const path = editMode.value ? `/waiters/${routeEntityId.value}` : '/waiters/'
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
    message.value = wasEdit ? 'Kellner aktualisiert.' : 'Kellner erstellt.'
    messageType.value = 'success'
    await goToList()
  } catch {
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
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = 'Kellner konnte nicht gelöscht werden.'
    messageType.value = 'error'
  }
}

onMounted(fetchWaiters)
</script>

<style scoped>
.empty-hint {
  opacity: 0.7;
  margin: 0 0 1rem;
}

h2 {
  margin: 0 0 1.5rem;
  color: rgb(var(--v-theme-on-surface));
}

label {
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

small,
.table-header span {
  opacity: 0.7;
  font-size: 0.9rem;
}

.actions {
  justify-content: flex-end;
  margin-top: 1.25rem;
}

.table-header h2 {
  margin: 0;
}

.search-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
</style>
