<template>
  <ListDetailLayout
    :title="$t('articles.title')"
    :subtitle="$t('articles.subtitle')"
    :createLabel="$t('articles.createLabel')"
    :showCreate="canCreateArticles"
    :showDetail="showDetail"
    @open-create="openCreateForm"
  >
    <template #detail>
      <h2>{{ editMode ? $t('articles.editTitle') : $t('articles.newTitle') }}</h2>
      <p class="form-required-legend"><span class="vq-asterisk">*</span> {{ $t('common.requiredLegend') }}</p>

      <v-form ref="formRef" @submit.prevent="saveArticle">
      <div class="form-field">
        <v-text-field
          v-model="form.name"
          :label="$t('common.name')"
          :placeholder="$t('articles.namePlaceholder')"
          hide-details="auto"
          required
          :rules="[rules.required]"
        />
      </div>

      <div class="form-field">
        <v-text-field
          v-model="form.label"
          :label="$t('common.label')"
          maxlength="22"
          :placeholder="$t('articles.labelPlaceholder')"
          hide-details="auto"
          required
          :rules="labelRules"
        />
        <small>{{ $t('articles.labelCharCount', { count: form.label.length }) }}</small>
      </div>

      <div class="form-field">
        <v-text-field
          v-model="form.importArticleNumber"
          :label="$t('articles.importArticleNumber')"
          :placeholder="$t('articles.importArticleNumberPlaceholder')"
          hide-details="auto"
        />
      </div>

      <div class="form-field">
        <v-textarea
          v-model="form.description"
          :label="$t('common.description')"
          rows="4"
          auto-grow
          :placeholder="$t('articles.descriptionPlaceholder')"
          hide-details="auto"
        />
      </div>

      <div class="field-row">
        <div class="form-field">
          <v-text-field v-model="form.unit" :label="$t('common.unit')" :placeholder="$t('articles.unitPlaceholder')" hide-details="auto" />
        </div>
      </div>

      <div v-if="showTaxCodeField" class="form-field">
        <v-select
          v-model="form.taxCodeId"
          :items="taxCodeOptions"
          item-title="title"
          item-value="value"
          :label="$t('articles.taxCode')"
          :loading="taxCodesLoading"
          hide-details="auto"
          required
          :rules="taxCodeRules"
        />
      </div>

      <div class="stock-field">
        <v-checkbox v-model="form.isAddition" :label="$t('articles.isAddition')" hide-details density="compact" />
      </div>
      <small v-if="form.isAddition" class="muted block-hint">
        {{ $t('articles.additionPriceHint') }}
      </small>

      <div class="field-row">
        <div class="form-field">
          <v-text-field
            v-model.number="form.price"
            type="number"
            step="0.01"
            :min="form.isAddition ? undefined : 0"
            :label="$t('common.price')"
            :prefix="formCurrency"
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
            :label="$t('common.category')"
            :placeholder="$t('articles.selectCategory')"
            hide-details="auto"
            required
            :rules="[rules.required]"
          />
        </div>
      </div>

      <div v-if="showAccountingAccountField" class="form-field">
        <v-select
          v-model="form.accountingAccountId"
          :items="accountingAccountOptions"
          item-title="title"
          item-value="value"
          :label="$t('articles.accountingAccount')"
          :placeholder="$t('common.optional')"
          :loading="accountingAccountsLoading"
          hide-details="auto"
          clearable
        />
      </div>

      <div v-if="editMode && activeId && !form.isAddition" class="additions-section">
        <h3>{{ $t('articles.additionsTitle') }}</h3>
        <p class="muted small">{{ $t('articles.additionsHint') }}</p>
        <div class="form-field">
          <v-select
            v-model="additionPickIds"
            :items="additionOptions"
            item-title="label"
            item-value="value"
            :label="$t('articles.addAddition')"
            :placeholder="$t('articles.selectAdditions')"
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
          <template #item.price="{ item }">{{ formatPrice(item.price, formCurrency) }}</template>
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
          <template #no-data>{{ $t('articles.noAdditionsLinked') }}</template>
        </VqDataTable>
        <v-btn
          color="primary"
          type="button"
          style="margin-top: 0.75rem"
          :disabled="!activeId"
          @click="saveAdditions"
        >
          {{ $t('articles.saveAdditions') }}
        </v-btn>
        <p v-if="additionsMessage" :class="additionsMessageType">{{ additionsMessage }}</p>
      </div>

      <div class="actions">
        <v-btn variant="outlined" type="button" @click="resetForm">{{ $t('common.back') }}</v-btn>
        <v-btn color="primary" type="submit">{{ $t('common.save') }}</v-btn>
      </div>
      <p v-if="message" :class="messageType">{{ message }}</p>
      </v-form>
    </template>

    <template #table>
      <p v-if="activeOrganisationId == null" class="empty-hint">
        {{ $t('common.noOrganisation') }}
      </p>
      <div class="table-header">
        <h2>{{ $t('articles.allTitle') }}</h2>
        <span>{{ $t('common.entriesCount', { filtered: filteredArticles.length, total: articlesInActiveOrganisation.length }) }}</span>
      </div>
      <div class="list-controls">
        <div class="search-field">
          <v-text-field
            v-model="searchQuery"
            :label="$t('common.search')"
            prepend-inner-icon="mdi-magnify"
            :placeholder="$t('articles.searchPlaceholder')"
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
            :label="$t('common.type')"
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
            :label="$t('common.category')"
            :placeholder="$t('articles.allCategories')"
            hide-details
            density="compact"
          />
        </div>
      </div>

      <VqDataTable
        v-model:page="currentPage"
        :headers="tableHeaders"
        :items="filteredArticles"
        :items-per-page="pageSize"
        item-value="id"
        class="vq-data-table list-table"
        hover
        @click:row="(_, { item }) => editArticle(item)"
      >
        <template #item.is_addition="{ item }">
          <v-chip :color="item.is_addition ? 'warning' : undefined" size="small" variant="tonal">
            {{ item.is_addition ? $t('articles.typeAddition') : $t('articles.typeArticle') }}
          </v-chip>
        </template>
        <template #item.price="{ item }">{{ formatPrice(item.price, item.organisation_currency) }}</template>
        <template #item.actions="{ item }">
          <v-btn color="error" variant="outlined" size="small" @click.stop="deleteArticle(item.id)">
            {{ $t('common.delete') }}
          </v-btn>
        </template>
        <template #no-data>{{ $t('articles.noData') }}</template>
      </VqDataTable>
    </template>
  </ListDetailLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ListDetailLayout from './ListDetailLayout.vue'
import { apiJson } from '../api'
import { useListDetailRouting } from '../composables/useListDetailRouting'
import { useClientPagination } from '../composables/useClientPagination'
import { invalidateOrgCatalog } from '../composables/useOrgCatalog'
import { matchesActiveOrganisation, organisationAccountsEnabled } from '../utils/orgScope'
import { rules, validateForm } from '../utils/formRules.js'
import { formatPriceWithCurrency } from '../utils/localeFormat.js'
import { useTaxCodes } from '../composables/useTaxCodes'
import { useAccountingAccounts } from '../composables/useAccountingAccounts'
import { SESSION_CONTEXT_KEY } from '../sessionContext'
import VqDataTable from './VqDataTable.vue'

const { t, locale } = useI18n()

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
const sessionContext = inject(SESSION_CONTEXT_KEY, null)
const organisationsList = computed(() => sessionContext?.accessibleOrganisations?.value ?? [])
const formCurrency = ref('EUR')
const activeId = computed(() => routeEntityId.value)
const message = ref('')
const messageType = ref('')
const searchQuery = ref('')
const categoryFilter = ref(null)
const typeFilter = ref('articles')
const additionsLocal = ref([])
const additionPickIds = ref([])
const additionsMessage = ref('')
const additionsMessageType = ref('')

const tableHeaders = computed(() => [
  { title: t('common.id'), key: 'id' },
  { title: t('common.type'), key: 'is_addition', sortable: false },
  { title: t('common.name'), key: 'name' },
  { title: t('articles.importNumberShort'), key: 'import_article_number' },
  { title: t('common.label'), key: 'label' },
  { title: t('common.unit'), key: 'unit' },
  { title: t('common.price'), key: 'price', sortable: false },
  { title: t('common.category'), key: 'article_category_name' },
  { title: t('common.organisation'), key: 'organisation_name' },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' },
])

const additionsHeaders = computed(() => [
  { title: t('articles.additionColumn'), key: 'name' },
  { title: t('common.price'), key: 'price', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end', width: 56 },
])

const emptyForm = () => ({
  name: '',
  label: '',
  importArticleNumber: '',
  description: '',
  unit: '',
  accountingAccountId: null,
  taxCodeId: null,
  price: 0,
  isAddition: false,
  articleCategoryId: null,
})

const typeFilterOptions = computed(() => [
  { value: 'articles', label: t('articles.typeArticle') },
  { value: 'additions', label: t('articles.typeAddition') },
  { value: 'all', label: t('articles.typeAll') },
])

const form = ref(emptyForm())

const activeOrganisation = computed(() => {
  if (props.activeOrganisationId == null) return null
  return organisationsList.value.find(
    (org) => Number(org.id) === Number(props.activeOrganisationId),
  ) ?? null
})

const showTaxCodeField = computed(() => Boolean(activeOrganisation.value?.vat_liable))
const showAccountingAccountField = computed(() =>
  organisationAccountsEnabled(organisationsList.value, props.activeOrganisationId),
)

const activeOrganisationCountryId = computed(() => activeOrganisation.value?.country_id ?? null)

const {
  options: taxCodeOptions,
  loading: taxCodesLoading,
} = useTaxCodes(activeOrganisationCountryId)

const {
  options: accountingAccountOptions,
  loading: accountingAccountsLoading,
  categoryDefaultAccountId,
} = useAccountingAccounts(() => props.activeOrganisationId)

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
  { value: null, label: t('articles.allCategories') },
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
      label: `${a.name} (${formatPrice(a.price, a.organisation_currency)})`,
    })),
)

const formRef = ref(null)

const labelRules = computed(() => [
  rules.required,
  (v) => String(v || '').length <= 22 || t('articles.labelMaxLength'),
])

const priceRules = computed(() => {
  const base = [rules.requiredNumber]
  if (!form.value.isAddition) base.push(rules.minNumber(0))
  return base
})

const taxCodeRules = computed(() => {
  if (!showTaxCodeField.value) return []
  return [rules.required]
})

function resolveDefaultAccountingAccountId(categoryId) {
  if (!showAccountingAccountField.value) return null
  const category = categories.value.find((row) => Number(row.id) === Number(categoryId))
  if (category?.accounting_account_id != null) {
    return category.accounting_account_id
  }
  return categoryDefaultAccountId.value
}

watch(
  () => form.value.articleCategoryId,
  (categoryId) => {
    if (editMode.value || categoryId == null) return
    if (form.value.accountingAccountId != null) return
    form.value.accountingAccountId = resolveDefaultAccountingAccountId(categoryId)
  },
)

function defaultTaxCodeIdForActiveOrganisation() {
  if (!showTaxCodeField.value) return null
  return activeOrganisation.value?.default_tax_code_id ?? null
}

function formatPrice(value, currency = 'EUR') {
  return formatPriceWithCurrency(value, currency || 'EUR', locale.value)
}

function currencyForOrganisationId(organisationId) {
  if (organisationId == null) return 'EUR'
  const org = organisationsList.value.find((o) => Number(o.id) === Number(organisationId))
  return org?.currency || 'EUR'
}

function syncFormCurrencyFromContext(article = null) {
  if (article?.organisation_currency) {
    formCurrency.value = article.organisation_currency
    return
  }
  if (article?.organisation_id != null) {
    formCurrency.value = currencyForOrganisationId(article.organisation_id)
    return
  }
  formCurrency.value = currencyForOrganisationId(props.activeOrganisationId)
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
    article.accounting_account_number,
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

const { currentPage, pageSize } = useClientPagination(filteredArticles, {
  resetOn: [searchQuery, categoryFilter, typeFilter, () => props.activeOrganisationId],
})

watch([searchQuery, categoryFilter, typeFilter, () => props.activeOrganisationId], () => {
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
    if (showDetail.value && isCreateMode.value) {
      syncFormCurrencyFromContext()
    }
    if (showDetail.value) goToList()
  },
)

async function fetchArticles() {
  try {
    articles.value = await apiJson('/articles/')
  } catch {
    message.value = t('articles.loadError')
    messageType.value = 'error'
  }
}

async function fetchCategories() {
  try {
    categories.value = await apiJson('/article-categories/')
  } catch {
    message.value = t('articles.categoriesLoadError')
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
  form.value.taxCodeId = defaultTaxCodeIdForActiveOrganisation()
  message.value = ''
  syncFormCurrencyFromContext()
}

async function applyArticleToForm(article) {
  form.value = {
    name: article.name || '',
    label: article.label || '',
    importArticleNumber: article.import_article_number || '',
    description: article.description || '',
    unit: article.unit || '',
    accountingAccountId: article.accounting_account_id ?? null,
    taxCodeId: article.tax_code_id ?? null,
    price: article.price ?? 0,
    isAddition: !!article.is_addition,
    articleCategoryId: article.article_category_id || null,
  }
  message.value = ''
  syncFormCurrencyFromContext(article)
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
    syncFormCurrencyFromContext()
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
      row = await apiJson(`/articles/${id}`)
    } catch {
      message.value = t('articles.notFound')
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
    const data = await apiJson(`/articles/${articleId}/additions`)
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
    const data = await apiJson(`/articles/${activeId.value}/additions`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: additionsLocal.value.map((l, idx) => ({
          addition_article_id: l.addition_article_id,
          sort_order: l.sort_order ?? idx,
        })),
      }),
    })
    additionsLocal.value = (data.items || []).map((row, idx) => ({
      addition_article_id: row.addition_article_id,
      name: row.name,
      price: row.price,
      sort_order: row.sort_order ?? idx,
    }))
    additionsMessage.value = t('articles.additionsSaved')
    additionsMessageType.value = 'success'
  } catch (e) {
    additionsMessage.value = e.message || t('common.saveFailed')
    additionsMessageType.value = 'error'
  }
}

async function saveArticle() {
  if (props.activeOrganisationId == null) {
    message.value = t('common.noOrganisation')
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
    accounting_account_id: showAccountingAccountField.value ? form.value.accountingAccountId : null,
    tax_code_id: showTaxCodeField.value ? form.value.taxCodeId : null,
    is_addition: form.value.isAddition,
    article_category_id: form.value.articleCategoryId,
  }

  try {
    const path = editMode.value ? `/articles/${activeId.value}` : '/articles/'
    const method = editMode.value ? 'PUT' : 'POST'
    await apiJson(path, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const wasEdit = editMode.value
    await fetchArticles()
    invalidateOrgCatalog(props.activeOrganisationId)
    message.value = wasEdit ? t('articles.updated') : t('articles.created')
    messageType.value = 'success'
    await goToList()
  } catch {
    message.value = t('articles.saveError')
    messageType.value = 'error'
  }
}

async function deleteArticle(id) {
  if (!confirm(t('articles.deleteConfirm'))) return
  try {
    await apiJson(`/articles/${id}`, {
      method: 'DELETE',
    })
    await fetchArticles()
    invalidateOrgCatalog(props.activeOrganisationId)
    message.value = t('articles.deleted')
    messageType.value = 'success'
    if (Number(routeEntityId.value) === Number(id)) {
      await goToList()
    }
  } catch {
    message.value = t('articles.deleteError')
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
.table-header span {
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
</style>
