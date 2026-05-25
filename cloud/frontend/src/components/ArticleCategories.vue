<template>
  <ListDetailLayout
    title="Artikelkategorien"
    subtitle="Artikelkategorien pro Organisation verwalten."
    createLabel="Neue Kategorie"
    :showCreate="canCreateCategories"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? 'Kategorie bearbeiten' : 'Neue Kategorie' }}</h2>

      <div class="form-field">
        <label>Name</label>
        <InputText v-model="form.name" placeholder="Getränke" />
      </div>

      <div class="actions">
        <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
        <Button label="Speichern" class="primary-button" :disabled="!canSave" @click="saveCategory" />
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        Bitte wählen Sie links eine Organisation.
      </p>
      <div class="table-header">
        <h2>Alle Kategorien</h2>
        <span>{{ filteredCategories.length }} von {{ categoriesInActiveOrganisation.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="searchQuery" placeholder="Name oder Organisation suchen..." />
          </IconField>
        </div>
      </div>

      <DataTable
        :value="paginatedCategories"
        dataKey="id"
        responsiveLayout="scroll"
        class="list-table"
        @row-click="editCategory($event.data)"
      >
        <template #empty>Keine Artikelkategorien gefunden.</template>
        <Column field="id" header="ID" />
        <Column field="name" header="Name" />
        <Column field="organisation_name" header="Organisation" />
        <Column field="article_count" header="Artikel" />
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button
              label="Löschen"
              class="danger"
              :disabled="data.article_count > 0"
              @click.stop="deleteCategory(data.id)"
            />
          </template>
        </Column>
      </DataTable>

      <div v-if="filteredCategories.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <Paginator
          :first="(currentPage - 1) * pageSize"
          :rows="pageSize"
          :totalRecords="filteredCategories.length"
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
import ListDetailLayout from './ListDetailLayout.vue'
import { apiFetch } from '../api'
import { matchesActiveOrganisation } from '../utils/orgScope'

const props = defineProps({
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

const categories = ref([])
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
})

const form = ref(emptyForm())

const canCreateCategories = computed(() => props.activeOrganisationId != null)

const canSave = computed(() => !!(props.activeOrganisationId != null && form.value.name))

function matchesSearch(category, term) {
  if (!term) return true
  return [category.id, category.name, category.organisation_name]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredCategories = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return categories.value.filter((category) => {
    if (!matchesSearch(category, term)) return false
    if (!matchesActiveOrganisation(props.activeOrganisationId, category.organisation_id)) return false
    return true
  })
})

const categoriesInActiveOrganisation = computed(() =>
  categories.value.filter((category) =>
    matchesActiveOrganisation(props.activeOrganisationId, category.organisation_id)
  )
)

const totalPages = computed(() => Math.max(1, Math.ceil(filteredCategories.value.length / pageSize)))

const paginatedCategories = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredCategories.value.slice(start, start + pageSize)
})

const paginationLabel = computed(() => {
  if (!filteredCategories.value.length) return '0 Einträge'
  const start = (currentPage.value - 1) * pageSize + 1
  const end = Math.min(currentPage.value * pageSize, filteredCategories.value.length)
  return `${start}-${end} von ${filteredCategories.value.length}`
})

watch([searchQuery, () => props.activeOrganisationId], () => {
  currentPage.value = 1
})

watch(
  () => props.activeOrganisationId,
  () => {
    if (showDetail.value) resetForm()
  },
)

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

async function fetchCategories() {
  try {
    const response = await apiFetch('/article-categories/')
    if (!response.ok) throw new Error(await response.text())
    categories.value = await response.json()
  } catch (error) {
    message.value = 'Artikelkategorien konnten nicht geladen werden.'
    messageType.value = 'error'
  }
}

function resetForm() {
  editMode.value = false
  activeId.value = null
  showDetail.value = false
  form.value = emptyForm()
  message.value = ''
}

function openCreateForm() {
  resetForm()
  showDetail.value = true
}

function editCategory(category) {
  showDetail.value = true
  editMode.value = true
  activeId.value = category.id
  form.value = {
    name: category.name || '',
  }
  message.value = ''
}

async function saveCategory() {
  const payload = {
    name: form.value.name,
  }
  if (!editMode.value) {
    payload.organisation_id = props.activeOrganisationId
  }

  try {
    const path = editMode.value ? `/article-categories/${activeId.value}` : '/article-categories/'
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
    await fetchCategories()
    resetForm()
    message.value = wasEdit ? 'Kategorie aktualisiert.' : 'Kategorie erstellt.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Fehler beim Speichern der Kategorie.'
    messageType.value = 'error'
  }
}

async function deleteCategory(id) {
  if (!confirm('Artikelkategorie wirklich löschen?')) return
  try {
    const response = await apiFetch(`/article-categories/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error(await response.text())
    await fetchCategories()
    message.value = 'Kategorie gelöscht.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Kategorie kann nur gelöscht werden, wenn keine Artikel verknüpft sind.'
    messageType.value = 'error'
  }
}

onMounted(fetchCategories)
</script>

<style scoped>
.empty-hint {
  color: var(--p-text-muted-color);
  margin: 0 0 1rem;
}

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
