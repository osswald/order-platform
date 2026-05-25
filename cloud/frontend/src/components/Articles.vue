<template>
  <ListDetailLayout
    title="Artikel"
    subtitle="Artikel und Lagerbestand pro Organisation verwalten."
    createLabel="Neuer Artikel"
    :showCreate="canCreateArticles"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? 'Artikel bearbeiten' : 'Neuer Artikel' }}</h2>

      <div class="form-field">
        <label>Name</label>
        <InputText v-model="form.name" placeholder="Espresso" />
      </div>

      <div class="form-field">
        <label>Label</label>
        <InputText v-model="form.label" maxlength="22" placeholder="Espresso" />
        <small>{{ form.label.length }}/22 Zeichen</small>
      </div>

      <div class="stock-field">
        <Checkbox v-model="form.isAddition" inputId="isAddition" binary />
        <label for="isAddition">Ist Zusatz</label>
      </div>
      <small v-if="form.isAddition" class="muted block-hint">
        Preis: 0 = kostenlos, positiv = Aufpreis, negativ = Abzug (vom Artikelpreis).
      </small>

      <div class="field-row">
        <div class="form-field">
          <label>Preis</label>
          <InputNumber
            v-model="form.price"
            mode="decimal"
            :min="form.isAddition ? undefined : 0"
            :minFractionDigits="2"
            :maxFractionDigits="2"
          />
        </div>
        <div class="form-field">
          <label>Kategorie</label>
          <Select
            v-model="form.articleCategoryId"
            :options="categoryOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Kategorie wählen"
            filter
          />
        </div>
      </div>

      <div class="stock-field">
        <Checkbox v-model="form.monitorStock" inputId="monitorStock" binary />
        <label for="monitorStock">Lagerbestand überwachen</label>
      </div>

      <div v-if="form.monitorStock" class="form-field">
        <label>Lagerbestand</label>
        <InputNumber v-model="form.inStock" :min="0" showButtons />
      </div>

      <div v-if="editMode && activeId && !form.isAddition" class="additions-section">
        <h3>Zusätze</h3>
        <p class="muted small">Preise der Zusätze unter Artikel → Zusätze pflegen. Hier nur verknüpfen.</p>
        <div class="form-field">
          <label>Zusatz hinzufügen</label>
          <MultiSelect
            v-model="additionPickIds"
            :options="additionOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Zusätze wählen"
            display="chip"
            filter
            class="w-full"
            @update:modelValue="onAdditionPick"
          />
        </div>
        <DataTable :value="additionsLocal" dataKey="addition_article_id" class="list-table nested" responsiveLayout="scroll">
          <Column field="name" header="Zusatz" />
          <Column header="Preis">
            <template #body="{ data }">{{ formatPrice(data.price) }}</template>
          </Column>
          <Column header="">
            <template #body="slotProps">
              <Button
                icon="pi pi-trash"
                text
                rounded
                type="button"
                severity="danger"
                @click="removeAdditionLink(slotProps.data)"
              />
            </template>
          </Column>
        </DataTable>
        <Button
          label="Zusätze speichern"
          class="primary-button"
          type="button"
          style="margin-top: 0.75rem"
          :disabled="!activeId"
          @click="saveAdditions"
        />
        <p v-if="additionsMessage" :class="additionsMessageType">{{ additionsMessage }}</p>
      </div>

      <div class="actions">
        <Button label="Zurück" class="secondary-button" type="button" @click="resetForm" />
        <Button label="Speichern" class="primary-button" :disabled="!canSave" @click="saveArticle" />
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
    </template>

    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        Bitte wählen Sie links eine Organisation.
      </p>
      <div class="table-header">
        <h2>Alle Artikel</h2>
        <span>{{ filteredArticles.length }} von {{ articlesInActiveOrganisation.length }} Einträgen</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <label>Suche</label>
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="searchQuery" placeholder="Name, Label oder Kategorie suchen..." />
          </IconField>
        </div>
        <div class="filter-field">
          <label>Typ</label>
          <Select
            v-model="typeFilter"
            :options="typeFilterOptions"
            optionLabel="label"
            optionValue="value"
          />
        </div>
        <div class="filter-field">
          <label>Kategorie</label>
          <Select
            v-model="categoryFilter"
            :options="categoryFilterOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Alle Kategorien"
            filter
          />
        </div>
      </div>

      <DataTable
        :value="paginatedArticles"
        dataKey="id"
        responsiveLayout="scroll"
        class="list-table"
        @row-click="editArticle($event.data)"
      >
        <template #empty>Keine Artikel gefunden.</template>
        <Column field="id" header="ID" />
        <Column header="Typ">
          <template #body="{ data }">
            <Tag :value="data.is_addition ? 'Zusatz' : 'Artikel'" :severity="data.is_addition ? 'warn' : 'secondary'" />
          </template>
        </Column>
        <Column field="name" header="Name" />
        <Column field="label" header="Label" />
        <Column header="Preis">
          <template #body="{ data }">{{ formatPrice(data.price) }}</template>
        </Column>
        <Column field="article_category_name" header="Kategorie" />
        <Column field="organisation_name" header="Organisation" />
        <Column header="Lager">
          <template #body="{ data }">
            <Tag
              v-if="data.monitor_stock"
              :value="`${data.in_stock ?? 0} Stk.`"
              severity="info"
            />
            <Tag v-else value="Aus" severity="secondary" />
          </template>
        </Column>
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button label="Löschen" class="danger" @click.stop="deleteArticle(data.id)" />
          </template>
        </Column>
      </DataTable>

      <div v-if="filteredArticles.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <Paginator
          :first="(currentPage - 1) * pageSize"
          :rows="pageSize"
          :totalRecords="filteredArticles.length"
          @page="currentPage = $event.page + 1"
        />
      </div>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Paginator from 'primevue/paginator'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiFetch } from '../api'
import { matchesActiveOrganisation } from '../utils/orgScope'

const props = defineProps({
  activeOrganisationId: {
    type: Number,
    default: null,
  },
})

const articles = ref([])
const categories = ref([])
const showDetail = ref(false)
const editMode = ref(false)
const activeId = ref(null)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const categoryFilter = ref(null)
const typeFilter = ref('articles')
const currentPage = ref(1)
const additionsLocal = ref([])
const additionPickIds = ref([])
const additionsMessage = ref('')
const additionsMessageType = ref('')
const pageSize = 20

const emptyForm = () => ({
  name: '',
  label: '',
  price: 0,
  isAddition: false,
  monitorStock: false,
  inStock: 0,
  articleCategoryId: null,
})

const typeFilterOptions = [
  { value: 'articles', label: 'Artikel' },
  { value: 'additions', label: 'Zusätze' },
  { value: 'all', label: 'Alle' },
]

const form = ref(emptyForm())

const visibleCategories = computed(() =>
  categories.value.filter((category) =>
    matchesActiveOrganisation(props.activeOrganisationId, category.organisation_id)
  )
)

const articlesInActiveOrganisation = computed(() =>
  articles.value.filter((article) =>
    matchesActiveOrganisation(props.activeOrganisationId, article.organisation_id)
  )
)

const categoryOptions = computed(() =>
  visibleCategories.value.map((category) => ({
    value: category.id,
    label: category.name,
  }))
)

const categoryFilterOptions = computed(() => [
  { value: null, label: 'Alle Kategorien' },
  ...categoryOptions.value,
])

const canCreateArticles = computed(
  () => props.activeOrganisationId != null && categoryOptions.value.length > 0,
)

const additionOptions = computed(() =>
  articles.value
    .filter(
      (a) =>
        a.is_addition &&
        matchesActiveOrganisation(props.activeOrganisationId, a.organisation_id) &&
        !additionsLocal.value.some((l) => l.addition_article_id === a.id),
    )
    .map((a) => ({
      value: a.id,
      label: `${a.name} (${formatPrice(a.price)})`,
    })),
)

const canSave = computed(() => {
  const priceOk =
    form.value.price !== null &&
    form.value.price !== undefined &&
    (form.value.isAddition || form.value.price >= 0)
  return !!(
    props.activeOrganisationId != null &&
    form.value.name &&
    form.value.label &&
    form.value.label.length <= 22 &&
    priceOk &&
    form.value.articleCategoryId &&
    (!form.value.monitorStock || (form.value.inStock !== null && form.value.inStock >= 0))
  )
})

function formatPrice(value) {
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR',
  }).format(value || 0)
}

function matchesSearch(article, term) {
  if (!term) return true
  return [
    article.id,
    article.name,
    article.label,
    article.price,
    article.article_category_name,
    article.organisation_name,
  ]
    .filter((value) => value !== null && value !== undefined)
    .some((value) => String(value).toLowerCase().includes(term))
}

const filteredArticles = computed(() => {
  const term = searchQuery.value.trim().toLowerCase()
  return articles.value.filter((article) => {
    if (!matchesSearch(article, term)) return false
    if (!matchesActiveOrganisation(props.activeOrganisationId, article.organisation_id)) return false
    if (categoryFilter.value != null && Number(article.article_category_id) !== Number(categoryFilter.value)) return false
    if (typeFilter.value === 'articles' && article.is_addition) return false
    if (typeFilter.value === 'additions' && !article.is_addition) return false
    return true
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredArticles.value.length / pageSize)))

const paginatedArticles = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredArticles.value.slice(start, start + pageSize)
})

const paginationLabel = computed(() => {
  if (!filteredArticles.value.length) return '0 Einträge'
  const start = (currentPage.value - 1) * pageSize + 1
  const end = Math.min(currentPage.value * pageSize, filteredArticles.value.length)
  return `${start}-${end} von ${filteredArticles.value.length}`
})

watch([searchQuery, categoryFilter, typeFilter, () => props.activeOrganisationId], () => {
  currentPage.value = 1
  if (
    categoryFilter.value != null &&
    !visibleCategories.value.some((category) => Number(category.id) === Number(categoryFilter.value))
  ) {
    categoryFilter.value = null
  }
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

async function fetchArticles() {
  try {
    const response = await apiFetch('/articles/')
    if (!response.ok) throw new Error(await response.text())
    articles.value = await response.json()
  } catch (error) {
    message.value = 'Artikel konnten nicht geladen werden.'
    messageType.value = 'error'
  }
}

async function fetchCategories() {
  try {
    const response = await apiFetch('/article-categories/')
    if (response.ok) {
      categories.value = await response.json()
    }
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
  additionsLocal.value = []
  additionPickIds.value = []
  additionsMessage.value = ''
  if (categoryOptions.value.length > 0) {
    form.value.articleCategoryId = categoryOptions.value[0].value
  }
  message.value = ''
}

function openCreateForm() {
  resetForm()
  form.value.isAddition = typeFilter.value === 'additions'
  showDetail.value = true
}

async function loadAdditions(articleId) {
  additionsLocal.value = []
  try {
    const resp = await apiFetch(`/articles/${articleId}/additions`)
    if (!resp.ok) return
    const data = await resp.json()
    additionsLocal.value = (data.items || []).map((row, idx) => ({
      addition_article_id: row.addition_article_id,
      name: row.name,
      price: row.price,
      sort_order: row.sort_order ?? idx,
    }))
  } catch {
    additionsLocal.value = []
  }
}

function editArticle(article) {
  showDetail.value = true
  editMode.value = true
  activeId.value = article.id
  form.value = {
    name: article.name || '',
    label: article.label || '',
    price: article.price ?? 0,
    isAddition: !!article.is_addition,
    monitorStock: !!article.monitor_stock,
    inStock: article.in_stock ?? 0,
    articleCategoryId: article.article_category_id || null,
  }
  message.value = ''
  if (!article.is_addition) loadAdditions(article.id)
  else {
    additionsLocal.value = []
  }
}

function onAdditionPick(ids) {
  const list = Array.isArray(ids) ? ids : []
  for (const id of list) {
    const art = articles.value.find((a) => a.id === id)
    if (!art || additionsLocal.value.some((l) => l.addition_article_id === id)) continue
    additionsLocal.value.push({
      addition_article_id: id,
      name: art.name,
      price: art.price,
      sort_order: additionsLocal.value.length,
    })
  }
  additionPickIds.value = []
}

function removeAdditionLink(row) {
  additionsLocal.value = additionsLocal.value.filter((l) => l.addition_article_id !== row.addition_article_id)
}

async function saveAdditions() {
  if (!activeId.value) return
  additionsMessage.value = ''
  try {
    const resp = await apiFetch(`/articles/${activeId.value}/additions`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: additionsLocal.value.map((l, idx) => ({
          addition_article_id: l.addition_article_id,
          sort_order: l.sort_order ?? idx,
        })),
      }),
    })
    if (!resp.ok) throw new Error(await resp.text())
    const data = await resp.json()
    additionsLocal.value = (data.items || []).map((row, idx) => ({
      addition_article_id: row.addition_article_id,
      name: row.name,
      price: row.price,
      sort_order: row.sort_order ?? idx,
    }))
    additionsMessage.value = 'Zusätze gespeichert.'
    additionsMessageType.value = 'success'
  } catch (e) {
    additionsMessage.value = e.message || 'Speichern fehlgeschlagen'
    additionsMessageType.value = 'error'
  }
}

async function saveArticle() {
  const payload = {
    name: form.value.name,
    label: form.value.label,
    price: form.value.price,
    is_addition: form.value.isAddition,
    monitor_stock: form.value.monitorStock,
    in_stock: form.value.monitorStock ? form.value.inStock : null,
    article_category_id: form.value.articleCategoryId,
  }

  try {
    const path = editMode.value ? `/articles/${activeId.value}` : '/articles/'
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
    await fetchArticles()
    resetForm()
    message.value = wasEdit ? 'Artikel aktualisiert.' : 'Artikel erstellt.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Fehler beim Speichern des Artikels.'
    messageType.value = 'error'
  }
}

async function deleteArticle(id) {
  if (!confirm('Artikel wirklich löschen?')) return
  try {
    const response = await apiFetch(`/articles/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error(await response.text())
    await fetchArticles()
    message.value = 'Artikel gelöscht.'
    messageType.value = 'success'
  } catch (error) {
    message.value = 'Artikel konnte nicht gelöscht werden.'
    messageType.value = 'error'
  }
}

onMounted(async () => {
  await fetchCategories()
  await fetchArticles()
})
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

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.block-hint {
  display: block;
  margin: -0.5rem 0 1rem;
}
.additions-section {
  margin: 1.5rem 0;
  padding-top: 1rem;
  border-top: 1px solid var(--p-content-border-color, #e2e8f0);
}
.additions-section h3 {
  margin: 0 0 0.5rem;
}
.stock-field {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0.5rem 0 1rem;
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
:deep(.p-inputnumber),
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
  grid-template-columns: minmax(240px, 1fr) 260px;
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

.success,
.error {
  margin-top: 1rem;
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
