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
      <p class="form-required-legend"><span class="vq-asterisk">*</span> Pflichtfeld</p>

      <v-form ref="formRef" @submit.prevent="saveArticle">
      <div class="form-field">
        <v-text-field
          v-model="form.name"
          label="Name"
          placeholder="Espresso"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>

      <div class="form-field">
        <v-text-field
          v-model="form.label"
          label="Label"
          maxlength="22"
          placeholder="Espresso"
          hide-details="auto"
          required
          :rules="labelRules"
        />
        <small>{{ form.label.length }}/22 Zeichen</small>
      </div>

      <div class="form-field">
        <v-text-field
          v-model="form.importArticleNumber"
          label="Import-Artikelnummer"
          placeholder="z. B. 4711"
          hide-details="auto"
        />
      </div>

      <div class="form-field">
        <v-textarea
          v-model="form.description"
          label="Beschreibung"
          rows="4"
          auto-grow
          placeholder="Optionale Beschreibung"
          hide-details="auto"
        />
      </div>

      <div class="field-row">
        <div class="form-field">
          <v-text-field v-model="form.unit" label="Einheit" placeholder="z. B. Stk., l, kg" hide-details="auto" />
        </div>
        <div class="form-field">
          <v-text-field
            v-model.number="form.incomeAccount"
            type="number"
            label="Erlöskonto"
            placeholder="Optional"
            hide-details="auto"
          />
        </div>
      </div>

      <div class="stock-field">
        <v-checkbox v-model="form.isAddition" label="Ist Zusatz" hide-details density="compact" />
      </div>
      <small v-if="form.isAddition" class="muted block-hint">
        Preis: 0 = kostenlos, positiv = Aufpreis, negativ = Abzug (vom Artikelpreis).
      </small>

      <div class="field-row">
        <div class="form-field">
          <v-text-field
            v-model.number="form.price"
            type="number"
            step="0.01"
            :min="form.isAddition ? undefined : 0"
            label="Preis"
            hide-details="auto"
            required
            :rules="priceRules"
          />
        </div>
        <div class="form-field">
          <v-select
            v-model="form.articleCategoryId"
            :items="categoryOptions"
            item-title="label"
            item-value="value"
            label="Kategorie"
            placeholder="Kategorie wählen"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>
      </div>

      <div class="stock-field">
        <v-checkbox v-model="form.monitorStock" label="Lagerbestand überwachen" hide-details density="compact" />
      </div>

      <div v-if="form.monitorStock" class="form-field">
        <v-text-field
          v-model.number="form.inStock"
          type="number"
          :min="0"
          label="Lagerbestand"
          hide-details="auto"
          required
          :rules="[rules.requiredNumber, rules.minNumber(0)]"
        />
      </div>

      <div v-if="editMode && activeId && !form.isAddition" class="additions-section">
        <h3>Zusätze</h3>
        <p class="muted small">Preise der Zusätze unter Artikel → Zusätze pflegen. Hier nur verknüpfen.</p>
        <div class="form-field">
          <v-select
            v-model="additionPickIds"
            :items="additionOptions"
            item-title="label"
            item-value="value"
            label="Zusatz hinzufügen"
            placeholder="Zusätze wählen"
            multiple
            chips
            closable-chips
            hide-details="auto"
            @update:model-value="onAdditionPick"
          />
        </div>
        <VqDataTable
          :headers="additionsHeaders"
          :items="additionsLocal"
          item-value="addition_article_id"
          class="vq-data-table list-table nested"
          hide-default-footer
        >
          <template #item.price="{ item }">{{ formatPrice(item.price) }}</template>
          <template #item.actions="{ item }">
            <v-btn
              icon="mdi-delete"
              variant="text"
              color="error"
              size="small"
              type="button"
              @click="removeAdditionLink(item)"
            />
          </template>
          <template #no-data>Keine Zusätze verknüpft.</template>
        </VqDataTable>
        <v-btn
          color="primary"
          type="button"
          style="margin-top: 0.75rem"
          :disabled="!activeId"
          @click="saveAdditions"
        >
          Zusätze speichern
        </v-btn>
        <p v-if="additionsMessage" :class="additionsMessageType">{{ additionsMessage }}</p>
      </div>

      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">Zurück</v-btn>
        <v-btn color="primary" type="submit">Speichern</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
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
          <v-text-field
            v-model="searchQuery"
            label="Suche"
            prepend-inner-icon="mdi-magnify"
            placeholder="Name, Label oder Kategorie suchen..."
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="typeFilter"
            :items="typeFilterOptions"
            item-title="label"
            item-value="value"
            label="Typ"
            hide-details
            density="compact"
          />
        </div>
        <div class="filter-field">
          <v-select
            v-model="categoryFilter"
            :items="categoryFilterOptions"
            item-title="label"
            item-value="value"
            label="Kategorie"
            placeholder="Alle Kategorien"
            hide-details
            density="compact"
          />
        </div>
      </div>

      <VqDataTable
        :headers="tableHeaders"
        :items="paginatedArticles"
        item-value="id"
        class="vq-data-table list-table"
        hide-default-footer
        hover
        @click:row="(_, { item }) => editArticle(item)"
      >
        <template #item.is_addition="{ item }">
          <v-chip :color="item.is_addition ? 'warning' : undefined" size="small" variant="tonal">
            {{ item.is_addition ? 'Zusatz' : 'Artikel' }}
          </v-chip>
        </template>
        <template #item.price="{ item }">{{ formatPrice(item.price) }}</template>
        <template #item.stock="{ item }">
          <v-chip v-if="item.monitor_stock" color="info" size="small" variant="tonal">
            {{ item.in_stock ?? 0 }} Stk.
          </v-chip>
          <v-chip v-else size="small" variant="tonal">Aus</v-chip>
        </template>
        <template #item.actions="{ item }">
          <v-btn color="error" variant="outlined" size="small" @click.stop="deleteArticle(item.id)">
            Löschen
          </v-btn>
        </template>
        <template #no-data>Keine Artikel gefunden.</template>
      </VqDataTable>

      <div v-if="filteredArticles.length" class="pagination">
        <span>{{ paginationLabel }}</span>
        <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" density="compact" />
      </div>
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
import { rules, validateForm } from '../utils/formRules.js'
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
} = useListDetailRouting('articles')

const articles = ref([])
const categories = ref([])
const activeId = computed(() => routeEntityId.value)
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

const tableHeaders = [
  { title: 'ID', key: 'id' },
  { title: 'Typ', key: 'is_addition', sortable: false },
  { title: 'Name', key: 'name' },
  { title: 'Import-Nr.', key: 'import_article_number' },
  { title: 'Label', key: 'label' },
  { title: 'Einheit', key: 'unit' },
  { title: 'Preis', key: 'price', sortable: false },
  { title: 'Kategorie', key: 'article_category_name' },
  { title: 'Organisation', key: 'organisation_name' },
  { title: 'Lager', key: 'stock', sortable: false },
  { title: 'Aktionen', key: 'actions', sortable: false, align: 'end' },
]

const additionsHeaders = [
  { title: 'Zusatz', key: 'name' },
  { title: 'Preis', key: 'price', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end', width: 56 },
]

const emptyForm = () => ({
  name: '',
  label: '',
  importArticleNumber: '',
  description: '',
  unit: '',
  incomeAccount: null,
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

const formRef = ref(null)

const labelRules = [
  rules.required,
  (v) => String(v || '').length <= 22 || 'Maximal 22 Zeichen',
]

const priceRules = computed(() => {
  const base = [rules.requiredNumber]
  if (!form.value.isAddition) base.push(rules.minNumber(0))
  return base
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
    article.import_article_number,
    article.label,
    article.description,
    article.unit,
    article.income_account,
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
    if (showDetail.value) goToList()
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

function clearFormState() {
  form.value = emptyForm()
  additionsLocal.value = []
  additionPickIds.value = []
  additionsMessage.value = ''
  if (categoryOptions.value.length > 0) {
    form.value.articleCategoryId = categoryOptions.value[0].value
  }
  message.value = ''
}

async function applyArticleToForm(article) {
  form.value = {
    name: article.name || '',
    label: article.label || '',
    importArticleNumber: article.import_article_number || '',
    description: article.description || '',
    unit: article.unit || '',
    incomeAccount: article.income_account ?? null,
    price: article.price ?? 0,
    isAddition: !!article.is_addition,
    monitorStock: !!article.monitor_stock,
    inStock: article.in_stock ?? 0,
    articleCategoryId: article.article_category_id || null,
  }
  message.value = ''
  if (!article.is_addition) await loadAdditions(article.id)
  else additionsLocal.value = []
}

async function syncRouteToForm() {
  if (!showDetail.value) {
    clearFormState()
    return
  }
  if (isCreateMode.value) {
    clearFormState()
    form.value.isAddition = typeFilter.value === 'additions'
    return
  }
  const id = routeEntityId.value
  if (id == null) {
    goToList()
    return
  }
  let row = articles.value.find((a) => Number(a.id) === Number(id))
  if (!row) {
    try {
      const response = await apiFetch(`/articles/${id}`)
      if (!response.ok) throw new Error(await response.text())
      row = await response.json()
    } catch {
      message.value = 'Artikel nicht gefunden.'
      messageType.value = 'error'
      goToList()
      return
    }
  }
  await applyArticleToForm(row)
}

watch(() => [route.name, route.params.id], syncRouteToForm, { immediate: true })

function resetForm() {
  goToList()
}

function openCreateForm() {
  goToCreate()
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

async function editArticle(article) {
  await applyArticleToForm(article)
  goToDetail(article.id)
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
  if (props.activeOrganisationId == null) {
    message.value = 'Bitte wählen Sie links eine Organisation.'
    messageType.value = 'error'
    return
  }
  if (!(await validateForm(formRef))) return
  const payload = {
    name: form.value.name,
    label: form.value.label,
    price: Number(form.value.price ?? 0),
    import_article_number: form.value.importArticleNumber || null,
    description: form.value.description || null,
    unit: form.value.unit || null,
    income_account: form.value.incomeAccount,
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
    message.value = wasEdit ? 'Artikel aktualisiert.' : 'Artikel erstellt.'
    messageType.value = 'success'
    await goToList()
  } catch {
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
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
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
  color: rgba(var(--v-theme-on-surface), 0.65);
  margin: 0 0 1rem;
}

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

.block-hint {
  display: block;
  margin: -0.5rem 0 1rem;
}
.additions-section {
  margin: 1.5rem 0;
  padding-top: 1rem;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
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
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.875rem;
  font-weight: 600;
}

small,
.table-header span,
.pagination {
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 0.9rem;
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
