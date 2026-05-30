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
        <v-text-field v-model="form.name" placeholder="Getränke" hide-details="auto" />
      </div>

      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
        <v-btn color="primary" :disabled="!canSave" @click="saveCategory">Speichern</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        Bitte wählen Sie links eine Organisation.
      </p>
      <div class="table-header">
        <h2>Alle Kategorien</h2>
        <span>{{ filteredCategories.length }} von {{ categoriesInActiveOrganisation.length }} Einträge</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <v-text-field
            v-model="searchQuery"
            placeholder="Name oder Organisation suchen..."
            prepend-inner-icon="mdi-magnify"
            hide-details="auto"
          />
        </div>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredCategories"
        :items-per-page="pageSize"
        item-value="id"
        hover
        no-data-text="Keine Artikelkategorien gefunden."
        class="vq-data-table list-table"
        @click:row="(_e, { item }) => editCategory(item)"
      >
        <template #item.actions="{ item }">
          <v-btn
            color="error"
            variant="text"
            :disabled="item.article_count > 0"
            @click.stop="deleteCategory(item.id)"
          >
            Löschen
          </v-btn>
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
} = useListDetailRouting('article-categories')

const tableHeaders = [
  { title: 'ID', key: 'id' },
  { title: 'Name', key: 'name' },
  { title: 'Organisation', key: 'organisation_name' },
  { title: 'Artikel', key: 'article_count' },
  { title: 'Aktionen', key: 'actions', sortable: false, align: 'end' },
]

const categories = ref([])
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

watch([searchQuery, () => props.activeOrganisationId], () => {
  currentPage.value = 1
})

watch(
  () => props.activeOrganisationId,
  () => {
    if (showDetail.value) goToList()
  },
)

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

function applyCategoryToForm(category) {
  form.value = { name: category.name || '' }
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
  let row = categories.value.find((c) => Number(c.id) === Number(id))
  if (!row) {
    try {
      const response = await apiFetch(`/article-categories/${id}`)
      if (!response.ok) throw new Error(await response.text())
      row = await response.json()
    } catch {
      message.value = 'Kategorie nicht gefunden.'
      messageType.value = 'error'
      goToList()
      return
    }
  }
  applyCategoryToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
}

function editCategory(category) {
  applyCategoryToForm(category)
  goToDetail(category.id)
}

async function saveCategory() {
  const payload = {
    name: form.value.name,
  }
  if (!editMode.value) {
    payload.organisation_id = props.activeOrganisationId
  }

  try {
    const path = editMode.value
      ? `/article-categories/${routeEntityId.value}`
      : '/article-categories/'
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
    message.value = wasEdit ? 'Kategorie aktualisiert.' : 'Kategorie erstellt.'
    messageType.value = 'success'
    await goToList()
  } catch {
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
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = 'Kategorie kann nur gelöscht werden, wenn keine Artikel verknüpft sind.'
    messageType.value = 'error'
  }
}

onMounted(fetchCategories)
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
